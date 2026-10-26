"""aiortc probe: drives a running fastrtc proof worker over real WebRTC and records an artifact.

Standalone client on purpose: it repeats the fastrtc wire constants instead of
importing the server, so a shared bug cannot make both sides agree. Protocol
source of truth: fastrtc ``frontend/shared/webrtc_utils.ts`` (data channel
``"text"`` created client-side, ``handshake`` on open, POST SDP offer,
trickle ICE candidates to the same route).

    cd apps/workers/fastrtc_voice && uv run --locked python tests/probe.py \
        --url http://127.0.0.1:8765 --out tests/artifacts/proof-local-modal.json

    --session-s holds the session open (keepalive stream included) that long,
    e.g. 75 s to prove survival past the platform's 60 s idle window.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import fractions
import json
import time
import uuid
from pathlib import Path
from typing import Any

import av
import httpx
import numpy as np
from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCSessionDescription
from aiortc.mediastreams import MediaStreamError, MediaStreamTrack

DATA_CHANNEL_LABEL = "text"
HANDSHAKE_MESSAGE = "handshake"
SAMPLE_RATE = 48000
FRAME_SAMPLES = 960  # 20 ms
TONE_HZ = 440.0
TONE_AMPLITUDE = 0.3
SECOND_TURN_HZ = 660.0
SESSION_S = 5.0
CONNECT_TIMEOUT_S = 30.0


class SineAudioTrack(MediaStreamTrack):
    """440 Hz sine, mono s16 48 kHz, 20 ms frames: the probe's voice."""

    kind = "audio"

    def __init__(self) -> None:
        super().__init__()
        self.frames = 0
        self._timestamp = 0
        self._phase = 0
        self.turn = 0
        self.frames_by_turn = [0, 0]

    async def recv(self) -> av.AudioFrame:
        if self.readyState != "live":
            raise MediaStreamError

        n = FRAME_SAMPLES
        hz = TONE_HZ if self.turn == 0 else SECOND_TURN_HZ
        samples = np.sin(2 * np.pi * hz * np.arange(self._phase, self._phase + n) / SAMPLE_RATE)
        self._phase = (self._phase + n) % SAMPLE_RATE

        frame = av.AudioFrame.from_ndarray(
            (samples * TONE_AMPLITUDE * 32767).astype(np.int16).reshape(1, -1),
            format="s16",
            layout="mono",
        )
        frame.sample_rate = SAMPLE_RATE
        frame.time_base = fractions.Fraction(1, SAMPLE_RATE)
        frame.pts = self._timestamp
        self._timestamp += n
        self.frames += 1
        self.frames_by_turn[self.turn] += 1

        await asyncio.sleep(n / SAMPLE_RATE)
        return frame


def candidate_types(sdp: str) -> list[str]:
    types: set[str] = set()
    for line in sdp.splitlines():
        if line.startswith("a=candidate:"):
            parts = line.split()
            if "typ" in parts:
                types.add(parts[parts.index("typ") + 1])
    return sorted(types)


def ice_evidence(pc: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"local": None, "remote": None, "remote_addr": None}
    try:
        sender = pc.getSenders()[0]
        connection = sender.transport.transport.iceGatherer._connection
        pair = connection._nominated.get(1)
        if pair is not None:
            out["remote"] = pair.remote_candidate.type
            local = pair.protocol.local_candidate
            out["local"] = local.type if local is not None else None
            out["remote_addr"] = str(getattr(pair, "remote_addr", None))
    except Exception:
        pass
    return out


async def probe(url: str, session_s: float = SESSION_S, bearer_token: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {
        "observed_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "url": url,
    }

    # Beam gates every endpoint behind the profile token; Modal ignores it.
    auth = {"Authorization": f"Bearer {bearer_token}"} if bearer_token else {}

    async with httpx.AsyncClient(
        base_url=url, timeout=httpx.Timeout(180.0, connect=10.0), headers=auth
    ) as client:
        healthz = await client.get("/healthz")
        result["healthz"] = {"status_code": healthz.status_code, "body": healthz.json()}

        rtc = await client.get("/rtc-configuration")
        ice_servers = rtc.json().get("iceServers", [])
        urls = [
            u
            for s in ice_servers
            for u in (s.get("urls") if isinstance(s.get("urls"), list) else [s.get("urls")])
        ]
        result["rtc_configuration"] = {
            "status_code": rtc.status_code,
            "ice_servers": len(ice_servers),
            "has_stun": any(u.startswith("stun:") for u in urls if u),
            "has_turn": any(u.startswith("turn") for u in urls if u),
        }

        webrtc_id = f"probe-{uuid.uuid4().hex[:12]}"
        pc = RTCPeerConnection(
            RTCConfiguration(
                iceServers=[
                    RTCIceServer(
                        urls=s.get("urls", []),
                        username=s.get("username"),
                        credential=s.get("credential"),
                    )
                    for s in ice_servers
                ]
            )
        )
        sine = SineAudioTrack()
        pc.addTrack(sine)

        stats: dict[str, Any] = {
            "inbound_frames": 0,
            "channel_open": False,
            "messages": [],
            "received_tone_frames": [0, 0],
        }
        tasks: set[asyncio.Task[None]] = set()

        def start_task(coro: Any) -> None:
            task = asyncio.create_task(coro)
            tasks.add(task)
            task.add_done_callback(tasks.discard)

        @pc.on("track")
        def on_track(track: Any) -> None:
            async def consume() -> None:
                while True:
                    try:
                        frame = await track.recv()
                        stats["inbound_frames"] += 1
                        raw = frame.to_ndarray()[0]
                        if not frame.format.is_planar:
                            raw = raw[:: len(frame.layout.channels)]
                        samples = raw.astype(np.float64)
                        if samples.size:
                            spectrum = np.abs(np.fft.rfft(samples))
                            peak = np.fft.rfftfreq(samples.size, 1 / frame.sample_rate)[
                                int(np.argmax(spectrum))
                            ]
                            rms = float(np.sqrt(np.mean(samples**2)))
                            if "audio_observation" not in stats:
                                stats["audio_observation"] = {
                                    "format": frame.format.name,
                                    "channels": len(frame.layout.channels),
                                    "rms": rms,
                                    "peak_hz": peak,
                                }
                            minimum_rms = 0.01 if np.issubdtype(raw.dtype, np.floating) else 100
                            if abs(peak - TONE_HZ) < 60 and rms > minimum_rms:
                                stats["received_tone_frames"][sine.turn] += 1
                    except MediaStreamError:
                        break

            start_task(consume())

        channel = pc.createDataChannel(DATA_CHANNEL_LABEL)

        @channel.on("open")
        def on_channel_open() -> None:
            stats["channel_open"] = True
            channel.send(HANDSHAKE_MESSAGE)

        @channel.on("message")
        def on_channel_message(message: Any) -> None:
            stats["messages"].append(str(message))

        async def send_candidate(candidate: Any) -> None:
            await client.post(
                "/webrtc/offer",
                json={
                    "candidate": candidate.toJSON(),
                    "webrtc_id": webrtc_id,
                    "type": "ice-candidate",
                },
            )

        @pc.on("icecandidate")
        def on_icecandidate(candidate: Any) -> None:
            if candidate is not None:
                start_task(send_candidate(candidate))

        await pc.setLocalDescription(await pc.createOffer())

        offer = await client.post(
            "/webrtc/offer",
            json={"sdp": pc.localDescription.sdp, "type": "offer", "webrtc_id": webrtc_id},
        )
        offer_body = offer.json()
        if offer.status_code != 200 or offer_body.get("status") == "failed":
            await pc.close()
            raise RuntimeError(f"offer rejected: {offer.status_code} {offer_body}")

        await pc.setRemoteDescription(
            RTCSessionDescription(sdp=offer_body["sdp"], type=offer_body["type"])
        )

        deadline = time.time() + CONNECT_TIMEOUT_S
        while pc.connectionState not in ("connected", "completed", "failed", "closed"):
            if time.time() > deadline:
                break
            await asyncio.sleep(0.1)
        connected = pc.connectionState in ("connected", "completed")
        connected_state = pc.connectionState

        keepalive: dict[str, Any] = {
            "live_status_code": None,
            "ticks": 0,
            "closed_status_code": None,
        }
        if connected:
            # Held open for the whole session: the in-flight keepalive request
            # is what makes the platform count the session as activity, so the
            # container cannot scale down mid-session.
            started = time.monotonic()
            async with client.stream("GET", f"/keepalive/{webrtc_id}") as keep:
                keepalive["live_status_code"] = keep.status_code
                async for line in keep.aiter_lines():
                    if line.startswith("event:"):
                        keepalive["ticks"] += 1
                        elapsed = time.monotonic() - started
                        if elapsed >= session_s / 2:
                            sine.turn = 1
                        if elapsed >= session_s:
                            break
            await asyncio.sleep(0.5)

        ice_pair = ice_evidence(pc) if connected else None

        await pc.close()
        if tasks:
            await asyncio.gather(*tasks)
        await asyncio.sleep(2.0)
        closed = await client.get(f"/keepalive/{webrtc_id}")
        keepalive["closed_status_code"] = closed.status_code

        result["session"] = {
            "webrtc_id": webrtc_id,
            "offer_status_code": offer.status_code,
            "answer_candidate_types": candidate_types(offer_body.get("sdp", "")),
            "connection_state": connected_state,
            "connected": connected,
            "data_channel_open": stats["channel_open"],
            "data_channel_messages": stats["messages"][:20],
            "outbound_frames": sine.frames,
            "inbound_frames": stats["inbound_frames"],
            "outbound_frames_by_turn": sine.frames_by_turn,
            "received_tone_frames_by_turn": stats["received_tone_frames"],
            "audio_observation": stats.get("audio_observation"),
            "session_s": session_s if connected else 0,
            "ice_pair": ice_pair,
        }
        result["keepalive"] = keepalive

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="fastrtc proof worker probe")
    parser.add_argument("--url", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--session-s", type=float, default=SESSION_S)
    parser.add_argument("--bearer-token", default="", help="Bearer token for gated URLs (Beam)")
    args = parser.parse_args()

    artifact = asyncio.run(probe(args.url, args.session_s, args.bearer_token))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, indent=2) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
