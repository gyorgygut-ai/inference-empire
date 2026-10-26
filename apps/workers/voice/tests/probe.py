"""aiortc probe: drives a running voice worker over real WebRTC and records an artifact.

Standalone client on purpose: it repeats the wire constants instead of importing
the server, so a shared bug cannot make both sides agree.

    cd apps/workers/voice && uv run --locked python tests/probe.py \
        --url http://127.0.0.1:8765 --out tests/artifacts/proof-local-modal.json
"""
from __future__ import annotations

import argparse
import asyncio
import fractions
import json
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import av
import httpx
import numpy as np
from aiortc import (
    RTCConfiguration,
    RTCIceServer,
    RTCPeerConnection,
    RTCSessionDescription,
)
from aiortc.mediastreams import MediaStreamError, MediaStreamTrack

if TYPE_CHECKING:
    from collections.abc import Callable

EVENTS_CHANNEL = "oai-events"
SAMPLE_RATE = 48000
FRAME_SAMPLES = 960
TONE_HZ = 440
TONE_AMPLITUDE = 0.3
SPEECH_RMS = 0.02

ICE_GATHER_TIMEOUT_S = 5.0
CONNECT_TIMEOUT_S = 20.0
EVENT_TIMEOUT_S = 30.0
SETTLE_S = 0.5


def rms(frame: av.AudioFrame) -> float:
    samples = np.frombuffer(bytes(frame.planes[0]), dtype=np.int16).astype(np.float64)
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(samples**2)) / 32768.0)


def silent_frame() -> av.AudioFrame:
    frame = av.AudioFrame(format="s16", layout="mono", samples=FRAME_SAMPLES)
    for plane in frame.planes:
        plane.update(bytes(plane.buffer_size))
    frame.sample_rate = SAMPLE_RATE
    frame.time_base = fractions.Fraction(1, SAMPLE_RATE)
    return frame


class EventLog:
    """Data-channel events plus an event-driven wait, no polling loop."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self._changed = asyncio.Event()

    def append(self, message: Any) -> None:
        self.events.append(json.loads(message))
        self._changed.set()

    def types(self) -> list[str]:
        return [event.get("type", "") for event in self.events]

    def first(self, event_type: str) -> dict[str, Any] | None:
        return next((e for e in self.events if e.get("type") == event_type), None)

    def transcripts(self) -> list[str]:
        found: list[str] = []
        for event in self.events:
            value = event.get("transcript") or event.get("delta")
            if isinstance(value, str):
                found.append(value)
        return found

    async def wait_until(
        self, predicate: Callable[[list[dict[str, Any]]], bool], timeout: float
    ) -> bool:
        deadline = time.monotonic() + timeout
        while True:
            if predicate(self.events):
                return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            self._changed.clear()
            try:
                await asyncio.wait_for(self._changed.wait(), remaining)
            except TimeoutError:
                return False


class ToneTrack(MediaStreamTrack):
    """Silence, with tone bursts requested by the probe."""

    kind = "audio"

    def __init__(self) -> None:
        super().__init__()
        self._start: float | None = None
        self._timestamp = 0
        self._tone_frames = 0
        self._phase = 0

    def burst(self, seconds: float) -> None:
        self._tone_frames += round(seconds / (FRAME_SAMPLES / SAMPLE_RATE))

    def _next(self) -> av.AudioFrame:
        if self._tone_frames <= 0:
            return silent_frame()

        self._tone_frames -= 1
        t = np.arange(FRAME_SAMPLES) + self._phase
        self._phase += FRAME_SAMPLES
        samples = (TONE_AMPLITUDE * 32767 * np.sin(2 * np.pi * TONE_HZ * t / SAMPLE_RATE)).astype(
            np.int16
        )
        frame = av.AudioFrame(format="s16", layout="mono", samples=FRAME_SAMPLES)
        frame.planes[0].update(samples.tobytes())
        frame.sample_rate = SAMPLE_RATE
        frame.time_base = fractions.Fraction(1, SAMPLE_RATE)
        return frame

    async def recv(self) -> av.AudioFrame:
        if self.readyState != "live":
            raise MediaStreamError

        frame = self._next()
        if self._start is None:
            self._start = time.time()
            self._timestamp = 0
        else:
            self._timestamp += frame.samples
            wait = self._start + (self._timestamp / SAMPLE_RATE) - time.time()
            if wait > 0:
                await asyncio.sleep(wait)

        frame.pts = self._timestamp
        return frame


class ClientSession:
    """One WebRTC session: offer, answer, data channel, echoed audio."""

    def __init__(self, url: str, ice_servers: list[RTCIceServer]) -> None:
        self.url = url
        self.pc = RTCPeerConnection(RTCConfiguration(iceServers=ice_servers))
        self.track = ToneTrack()
        self.log = EventLog()
        self.audio: list[av.AudioFrame] = []
        self.status_code = 0
        self.answer_sdp = ""
        self.ice_state = ""
        self._channel: Any = None
        self._consumers: list[asyncio.Task[None]] = []

        self.pc.addTrack(self.track)
        self.pc.on("track", self._on_track)
        self.pc.on("connectionstatechange", self._on_state)

    def _on_state(self) -> None:
        self.ice_state = self.pc.connectionState

    @property
    def channel(self) -> Any:
        return self._channel

    def _on_track(self, track: Any) -> None:
        if track.kind != "audio":
            return

        async def consume() -> None:
            while True:
                try:
                    self.audio.append(await track.recv())
                except MediaStreamError:
                    break

        self._consumers.append(asyncio.ensure_future(consume()))

    async def connect(self, client: httpx.AsyncClient) -> None:
        self._channel = self.pc.createDataChannel(EVENTS_CHANNEL)
        self._channel.on("message", self.log.append)

        await self.pc.setLocalDescription(await self.pc.createOffer())
        await self._wait_for_ice_gathering()

        response = await client.post(
            f"{self.url}/v1/realtime/calls",
            content=self.pc.localDescription.sdp,
            headers={"Content-Type": "application/sdp"},
        )
        self.status_code = response.status_code
        self.answer_sdp = response.text
        response.raise_for_status()

        await self.pc.setRemoteDescription(
            RTCSessionDescription(sdp=self.answer_sdp, type="answer")
        )
        await self._wait_for_connection()

    async def _wait_for_ice_gathering(self) -> None:
        if self.pc.iceGatheringState == "complete":
            return
        done = asyncio.Event()

        @self.pc.on("icegatheringstatechange")
        def _on_change() -> None:
            if self.pc.iceGatheringState == "complete":
                done.set()

        try:
            await asyncio.wait_for(done.wait(), ICE_GATHER_TIMEOUT_S)
        except TimeoutError:
            pass

    async def _wait_for_connection(self) -> None:
        deadline = time.monotonic() + CONNECT_TIMEOUT_S
        while self.pc.connectionState != "connected" and time.monotonic() < deadline:
            await asyncio.sleep(0.05)

    async def close(self) -> None:
        for task in self._consumers:
            task.cancel()
        self._consumers.clear()
        self.track.stop()
        await self.pc.close()

    # -- observations ------------------------------------------------------

    def answer_candidate_types(self) -> list[str]:
        found = [
            line.split(" typ ")[1].split()[0]
            for line in self.answer_sdp.splitlines()
            if line.startswith("a=candidate:") and " typ " in line
        ]
        return sorted(set(found))

    def voiced(self) -> dict[str, Any]:
        loud = [frame for frame in self.audio if rms(frame) > SPEECH_RMS]
        seconds = sum(frame.samples for frame in loud) / SAMPLE_RATE
        level = float(np.mean([rms(frame) for frame in loud])) if loud else 0.0
        return {
            "frames": len(self.audio),
            "voiced_frames": len(loud),
            "voiced_seconds": round(seconds, 2),
            "rms": round(level, 4),
        }


async def run_session(
    url: str,
    ice_servers: list[RTCIceServer],
    client: httpx.AsyncClient,
    *,
    turns: int,
    idle_seconds: float,
    check_append: bool,
) -> dict[str, Any]:
    session = ClientSession(url, ice_servers)
    try:
        await session.connect(client)
        note(f"connected, answer candidates {session.answer_candidate_types()}")

        opened = await session.log.wait_until(
            lambda events: any(e.get("type") == "session.created" for e in events),
            CONNECT_TIMEOUT_S,
        )
        if not opened:
            raise RuntimeError("session.created never arrived")
        note("session.created received")

        observations: dict[str, Any] = {}
        for turn in range(1, turns + 1):
            note(f"turn {turn}: sending 2 s of tone")
            session.track.burst(2.0)
            completed = await session.log.wait_until(
                lambda events, turn=turn: sum(
                    1 for e in events if e.get("type") == "response.done"
                )
                >= turn,
                EVENT_TIMEOUT_S,
            )
            if not completed:
                raise RuntimeError(f"turn {turn} never completed")
            note(f"turn {turn} completed, {len(session.log.events)} events")

            if turn == 1 and check_append:
                session.channel.send(
                    json.dumps({"type": "input_audio_buffer.append", "audio": "AAAA"})
                )
                rejected = await session.log.wait_until(
                    lambda events: any(e.get("type") == "error" for e in events),
                    EVENT_TIMEOUT_S,
                )
                if not rejected:
                    raise RuntimeError("input_audio_buffer.append was not rejected")
                error = session.log.first("error") or {}
                observations["append_rejection"] = {
                    "code": (error.get("error") or {}).get("code"),
                    "dc_state_after": session.channel.readyState,
                }

            if idle_seconds > 0 and turn < turns:
                note(f"idling {idle_seconds:.0f} s")
                remaining = idle_seconds
                while remaining > 0:
                    step = min(30.0, remaining)
                    await asyncio.sleep(step)
                    remaining -= step
                    if remaining > 0:
                        note(
                            f"  idle {idle_seconds - remaining:.0f}/{idle_seconds:.0f}s "
                            f"state {session.pc.connectionState}"
                        )
                observations["idle_seconds"] = idle_seconds
                observations["state_after_idle"] = session.pc.connectionState

        await asyncio.sleep(SETTLE_S)
        return {
            "status_code": session.status_code,
            "ice_connection_state": session.ice_state,
            "answer_candidate_types": session.answer_candidate_types(),
            "event_types": session.log.types(),
            "events": session.log.events,
            "transcripts": session.log.transcripts(),
            "audio": session.voiced(),
            **observations,
        }
    finally:
        note("closing session")
        await session.close()
        note("session closed")


def note(message: str) -> None:
    print(f"[probe] {message}", file=sys.stderr, flush=True)


def rtc_servers(payload: dict[str, Any]) -> list[RTCIceServer]:
    servers: list[RTCIceServer] = []
    for entry in payload.get("iceServers", []):
        urls = entry.get("urls")
        if not urls:
            continue
        servers.append(
            RTCIceServer(
                urls=urls,
                username=entry.get("username"),
                credential=entry.get("credential"),
            )
        )
    return servers


def _urls(entry: dict[str, Any]) -> list[str]:
    urls = entry.get("urls")
    if isinstance(urls, str):
        return [urls]
    return list(urls or [])


def auth_headers(token: str) -> dict[str, str]:
    """Beam gates every endpoint behind the profile token; Modal ignores it."""
    return {"Authorization": f"Bearer {token}"} if token else {}


async def run_probe(
    url: str, target: str, idle_seconds: float, turns: int, bearer_token: str = ""
) -> dict[str, Any]:
    started = time.monotonic()
    artifact: dict[str, Any] = {"target": target, "url": url, "started_at": time.time()}
    auth = auth_headers(bearer_token)

    async with httpx.AsyncClient(timeout=CONNECT_TIMEOUT_S, headers=auth) as client:
        health = await client.get(f"{url}/healthz")
        artifact["healthz"] = {"status_code": health.status_code, "body": health.json()}

        credentials = await client.get(f"{url}/turn-credentials")
        payload = credentials.json()
        turn_urls = [
            uri
            for entry in payload.get("iceServers", [])
            for uri in _urls(entry)
            if uri.startswith("turn")
        ]
        if credentials.status_code != 200:
            raise RuntimeError(f"/turn-credentials returned {credentials.status_code}: {payload}")

        artifact["turn_credentials"] = {
            "status_code": credentials.status_code,
            "turn_urls": turn_urls,
            "has_username": any(bool(e.get("username")) for e in payload.get("iceServers", [])),
            "has_credential": any(
                bool(e.get("credential")) for e in payload.get("iceServers", [])
            ),
        }

        wrong_type = await client.post(
            f"{url}/v1/realtime/calls",
            content=b"{}",
            headers={"Content-Type": "application/json"},
        )
        artifact["wrong_content_type"] = {"status_code": wrong_type.status_code}

        malformed = await client.post(
            f"{url}/v1/realtime/calls",
            content=b"v=0\n",
            headers={"Content-Type": "application/sdp"},
        )
        artifact["malformed_sdp"] = {"status_code": malformed.status_code}

        ice_servers = rtc_servers(payload)
        note("session 1")
        artifact["session_1"] = await run_session(
            url, ice_servers, client, turns=turns, idle_seconds=idle_seconds, check_append=True
        )

        await asyncio.sleep(2.0)
        note("session 2 (reconnect)")
        artifact["session_2"] = await run_session(
            url, ice_servers, client, turns=1, idle_seconds=0, check_append=False
        )

    artifact["duration_seconds"] = round(time.monotonic() - started, 1)
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--out", required=True)
    parser.add_argument("--target", default="local")
    parser.add_argument("--idle-seconds", type=float, default=0.0)
    parser.add_argument("--turns", type=int, default=2)
    parser.add_argument("--bearer-token", default="", help="Bearer token for gated URLs (Beam)")
    args = parser.parse_args()

    artifact = asyncio.run(
        run_probe(args.url, args.target, args.idle_seconds, args.turns, args.bearer_token)
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, indent=2))
    summary = {
        "target": artifact["target"],
        "url": artifact["url"],
        "healthz": artifact["healthz"],
        "turn_credentials": artifact["turn_credentials"],
        "wrong_content_type": artifact["wrong_content_type"],
        "malformed_sdp": artifact["malformed_sdp"],
        "session_1": {
            key: artifact["session_1"][key]
            for key in (
                "status_code",
                "ice_connection_state",
                "answer_candidate_types",
                "event_types",
                "transcripts",
                "audio",
                "append_rejection",
                "idle_seconds",
                "state_after_idle",
            )
            if key in artifact["session_1"]
        },
        "session_2": {
            key: artifact["session_2"][key]
            for key in ("ice_connection_state", "event_types", "transcripts", "audio")
        },
        "duration_seconds": artifact["duration_seconds"],
        "out": str(out),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
