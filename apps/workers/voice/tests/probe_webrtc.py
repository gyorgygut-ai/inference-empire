"""Exercise a real FastRTC WebRTC turn and retain sanitized playable audio proof."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
import uuid
from fractions import Fraction
from pathlib import Path

import av
import httpx
import numpy as np
import soundfile as sf
from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCSessionDescription
from aiortc.mediastreams import MediaStreamError, MediaStreamTrack

RATE = 48_000
FRAME = 960
RESPONSE_TIMEOUT_SECONDS = 600


class SpeechTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self, audio: np.ndarray):
        super().__init__()
        self.audio = audio
        self.offset = 0
        self.pts = 0
        self.started = time.monotonic()

    async def recv(self) -> av.AudioFrame:
        samples = np.zeros(FRAME, dtype=np.int16)
        count = min(FRAME, len(self.audio) - self.offset)
        if count > 0:
            samples[:count] = self.audio[self.offset : self.offset + count]
            self.offset += count
        self.pts += FRAME
        delay = self.started + self.pts / RATE - time.monotonic()
        if delay > 0:
            await asyncio.sleep(delay)
        frame = av.AudioFrame(format="s16", layout="mono", samples=FRAME)
        frame.planes[0].update(samples.tobytes())
        frame.sample_rate = RATE
        frame.pts = self.pts - FRAME
        frame.time_base = Fraction(1, RATE)
        return frame


def load_speech(path: Path) -> np.ndarray:
    audio, rate = sf.read(path, dtype="float32", always_2d=True)
    mono = audio.mean(axis=1)
    converted = np.interp(
        np.linspace(0, len(mono) - 1, round(len(mono) * RATE / rate)),
        np.arange(len(mono)), mono,
    )
    if float(np.max(np.abs(converted))) < 0.005:
        raise ValueError("speech fixture is silent")
    return np.clip(converted * 32767, -32768, 32767).astype(np.int16)


async def run(url: str, token: str, voice: str, input_path: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    session_id = str(uuid.uuid4())
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    timeout = httpx.Timeout(30.0, read=300.0)
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        assets = (await client.get(f"{url}/v1/voice-assets")).raise_for_status()
        voice_asset = assets.json()[voice]
        ice = (await client.get(f"{url}/v1/rtc-configuration")).raise_for_status().json()
        configuration = RTCConfiguration(
            iceServers=[RTCIceServer(**entry) for entry in ice.get("iceServers", [])]
        )
        peer = RTCPeerConnection(configuration)
        peer.addTrack(SpeechTrack(load_speech(input_path)))
        connected = asyncio.Event()
        voiced = asyncio.Event()
        response: list[np.ndarray] = []
        consumers: list[asyncio.Task] = []
        state = {"connection": "new", "sample_rate": RATE}

        @peer.on("connectionstatechange")
        async def connection_changed():
            state["connection"] = peer.connectionState
            if peer.connectionState == "connected":
                connected.set()

        @peer.on("track")
        def incoming(track):
            print(f"received remote {track.kind} track", file=sys.stderr, flush=True)

            async def consume():
                while True:
                    try:
                        frame = await track.recv()
                    except MediaStreamError:
                        return
                    samples = np.frombuffer(bytes(frame.planes[0]), dtype=np.int16).copy()
                    response.append(samples)
                    if np.sqrt(np.mean(samples.astype(np.float32) ** 2)) > 160:
                        voiced.set()

            consumers.append(asyncio.create_task(consume()))

        try:
            await peer.setLocalDescription(await peer.createOffer())
            await asyncio.wait_for(_ice_complete(peer), timeout=30)
            offer = {
                "sdp": peer.localDescription.sdp,
                "type": peer.localDescription.type,
                "webrtc_id": session_id,
            }
            answer = (await client.post(f"{url}/webrtc/offer", json=offer)).raise_for_status()
            await peer.setRemoteDescription(RTCSessionDescription(**answer.json()))
            await asyncio.wait_for(connected.wait(), timeout=45)
            try:
                await asyncio.wait_for(voiced.wait(), timeout=RESPONSE_TIMEOUT_SECONDS)
            except TimeoutError as error:
                raise TimeoutError(
                    f"no response audio; connection={state['connection']}, frames={len(response)}, "
                    f"session_id={session_id}"
                ) from error
            await asyncio.sleep(8)
        finally:
            await peer.close()
            for consumer in consumers:
                consumer.cancel()

    audio = np.concatenate(response) if response else np.zeros(0, dtype=np.int16)
    if audio.size == 0 or float(np.sqrt(np.mean(audio.astype(np.float32) ** 2))) <= 160:
        raise AssertionError("WebRTC returned no non-silent response audio")
    input_copy, output_path = output_dir / f"{session_id}-input.wav", output_dir / f"{session_id}-output.wav"
    sf.write(input_copy, load_speech(input_path).astype(np.float32) / 32767, RATE)
    sf.write(output_path, audio, state["sample_rate"])
    report = {
        "session_id": session_id,
        "state": state,
        "voice_id": voice,
        "voice_sha256": voice_asset["sha256"],
        "voice_asset_path": voice_asset["loaded"],
        "input_audio": str(input_copy),
        "input_sha256": hashlib.sha256(input_copy.read_bytes()).hexdigest(),
        "output_audio": str(output_path),
        "output_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
        "output_samples": int(audio.size),
        "output_rms": round(float(np.sqrt(np.mean(audio.astype(np.float32) ** 2))), 2),
    }
    (output_dir / f"{session_id}.json").write_text(json.dumps(report, indent=2))
    return report


async def _ice_complete(peer: RTCPeerConnection) -> None:
    if peer.iceGatheringState == "complete":
        return
    changed = asyncio.Event()

    @peer.on("icegatheringstatechange")
    def gathering_changed():
        if peer.iceGatheringState == "complete":
            changed.set()

    await changed.wait()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--token", default="")
    parser.add_argument("--voice", default="GutAI")
    parser.add_argument("--input", type=Path, default=Path(".proof/input.wav"))
    parser.add_argument("--output-dir", type=Path, default=Path(".proof"))
    args = parser.parse_args()
    report = asyncio.run(run(args.url.rstrip("/"), args.token, args.voice, args.input, args.output_dir))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
