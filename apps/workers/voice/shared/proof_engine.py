"""Throwaway proof engine: real WebRTC, dummy Realtime events.

Deleted at Level 3, where the upstream ``create_app(pool, stop_event)``
from ``speech-to-speech`` takes over. The event contract and the tests
carry over unchanged.
"""
from __future__ import annotations

import asyncio
import fractions
import json
import logging
import time
import uuid
from typing import TYPE_CHECKING, Any

import av
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

log = logging.getLogger(__name__)

EVENTS_CHANNEL = "oai-events"
SAMPLE_RATE = 48000
FRAME_SAMPLES = 960  # 20 ms of Opus audio
SPEECH_RMS = 0.02
TURN_END_SILENCE_FRAMES = 10  # 200 ms of silence closes a turn


def rtc_ice_servers(payload: dict[str, Any]) -> list[RTCIceServer]:
    """Browser-format ``iceServers`` (HF proxy) to aiortc ice servers."""
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
                credentialType=entry.get("credentialType", "password"),
            )
        )
    return servers


def rms(frame: av.AudioFrame) -> float:
    """Root-mean-square amplitude of an s16 frame, normalised to 0..1."""
    samples = np.frombuffer(bytes(frame.planes[0]), dtype=np.int16).astype(np.float64)
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(samples**2)) / 32768.0)


def silence() -> av.AudioFrame:
    """Silence in the exact wire format the Opus decoder emits.

    aiortc's Opus encoder resampler locks its input layout on the first frame,
    so every frame leaving this track must be s16/stereo/48 kHz/960 samples.
    """
    frame = av.AudioFrame(format="s16", layout="stereo", samples=FRAME_SAMPLES)
    for plane in frame.planes:
        plane.update(bytes(plane.buffer_size))
    frame.sample_rate = SAMPLE_RATE
    frame.time_base = fractions.Fraction(1, SAMPLE_RATE)
    return frame


class EchoAudioTrack(MediaStreamTrack):
    """Sends the client audio back; silence while nothing is queued."""

    kind = "audio"

    def __init__(self) -> None:
        super().__init__()
        self._queue: asyncio.Queue[av.AudioFrame] = asyncio.Queue(maxsize=200)
        self._start: float | None = None
        self._timestamp = 0

    def push(self, frame: av.AudioFrame) -> None:
        if self._queue.full():
            self._queue.get_nowait()
        self._queue.put_nowait(frame)

    async def recv(self) -> av.AudioFrame:
        if self.readyState != "live":
            raise MediaStreamError

        try:
            frame = self._queue.get_nowait()
        except asyncio.QueueEmpty:
            frame = silence()

        if self._start is None:
            self._start = time.time()
            self._timestamp = 0
        else:
            self._timestamp += frame.samples
            wait = self._start + (self._timestamp / SAMPLE_RATE) - time.time()
            if wait > 0:
                await asyncio.sleep(wait)

        frame.pts = self._timestamp
        frame.sample_rate = SAMPLE_RATE
        frame.time_base = fractions.Fraction(1, SAMPLE_RATE)
        return frame


class ProofPeer:
    """One WebRTC peer: answers an SDP offer and emits the dummy protocol."""

    def __init__(self, ice_servers: list[RTCIceServer]) -> None:
        self.id = f"proof-{uuid.uuid4().hex[:12]}"
        self.pc = RTCPeerConnection(RTCConfiguration(iceServers=ice_servers))
        self.echo = EchoAudioTrack()
        self.pc.addTrack(self.echo)

        self.events: list[dict[str, Any]] = []
        self.turns = 0

        self._channel: Any = None
        self._announced = False
        self._speaking = False
        self._silent_frames = 0
        self._consumers: list[asyncio.Task[None]] = []
        self._released = False
        self._closer: asyncio.Task[None] | None = None
        self.on_release: Callable[[str], None] | None = None

        self.pc.on("datachannel", self._on_datachannel)
        self.pc.on("track", self._on_track)
        self.pc.on("connectionstatechange", self._on_state)

    # -- signaling ---------------------------------------------------------

    async def answer(self, offer: str, gather_timeout: float) -> str:
        await self.pc.setRemoteDescription(RTCSessionDescription(sdp=offer, type="offer"))
        await self.pc.setLocalDescription(await self.pc.createAnswer())
        await self._wait_for_ice_gathering(gather_timeout)
        return self.pc.localDescription.sdp

    async def _wait_for_ice_gathering(self, timeout: float) -> None:
        if self.pc.iceGatheringState == "complete":
            return

        done = asyncio.Event()

        @self.pc.on("icegatheringstatechange")
        def _on_change() -> None:
            if self.pc.iceGatheringState == "complete":
                done.set()

        try:
            await asyncio.wait_for(done.wait(), timeout)
        except TimeoutError:
            log.warning("ice gathering did not complete within %.1fs", timeout)

    async def close(self) -> None:
        for task in self._consumers:
            task.cancel()
        self._consumers.clear()
        self.echo.stop()
        await self.pc.close()

    def _release(self) -> None:
        """Drop the peer once the client is gone; idempotent."""
        if self._released:
            return
        self._released = True
        log.info("peer %s released", self.id)
        if self.on_release is not None:
            self.on_release(self.id)
        self._closer = asyncio.ensure_future(self.close())

    def _on_state(self) -> None:
        state = self.pc.connectionState
        log.info("peer %s connection state %s", self.id, state)
        if state in ("failed", "closed"):
            self._release()

    # -- data channel ------------------------------------------------------

    def _on_datachannel(self, channel: Any) -> None:
        if channel.label != EVENTS_CHANNEL:
            return
        self._channel = channel
        channel.on("message", self._on_message)
        channel.on("close", self._release)
        if channel.readyState == "open":
            self._announce()
        else:
            channel.on("open", self._announce)

    def _announce(self) -> None:
        if self._announced:
            return
        self._announced = True
        self.emit(
            {
                "type": "session.created",
                "session": {"id": self.id, "mode": "proof"},
            }
        )

    def _on_message(self, message: Any) -> None:
        try:
            event = json.loads(message)
        except (TypeError, ValueError):
            return

        if event.get("type") == "input_audio_buffer.append":
            self.emit(
                {
                    "type": "error",
                    "error": {
                        "type": "invalid_request_error",
                        "code": "invalid_event_for_transport",
                        "message": (
                            "input_audio_buffer.append is not supported over WebRTC; "
                            "send audio on the RTP track."
                        ),
                    },
                }
            )

    def emit(self, event: dict[str, Any]) -> None:
        event = {"event_id": f"evt_{uuid.uuid4().hex[:16]}", **event}
        self.events.append(event)
        if self._channel is not None and self._channel.readyState == "open":
            self._channel.send(json.dumps(event))

    # -- media -------------------------------------------------------------

    def _on_track(self, track: Any) -> None:
        if track.kind != "audio":
            return
        self._consumers.append(asyncio.ensure_future(self._consume(track)))

    async def _consume(self, track: Any) -> None:
        while True:
            try:
                frame = await track.recv()
            except MediaStreamError:
                break
            self.echo.push(frame)
            self._detect_speech(frame)

    def _detect_speech(self, frame: av.AudioFrame) -> None:
        if rms(frame) >= SPEECH_RMS:
            self._silent_frames = 0
            if not self._speaking:
                self._speaking = True
                self.emit({"type": "input_audio_buffer.speech_started"})
            return

        if not self._speaking:
            return

        self._silent_frames += 1
        if self._silent_frames < TURN_END_SILENCE_FRAMES:
            return

        self._speaking = False
        self._silent_frames = 0
        self._finish_turn()

    def _finish_turn(self) -> None:
        self.turns += 1
        turn = self.turns
        self.emit({"type": "input_audio_buffer.speech_stopped"})
        self.emit(
            {
                "type": "conversation.item.input_audio_transcription.completed",
                "transcript": f"proof-turn-{turn}",
            }
        )
        self.emit({"type": "response.created"})
        self.emit(
            {
                "type": "response.output_audio_transcript.delta",
                "delta": f"proof-reply-{turn}",
            }
        )
        self.emit(
            {
                "type": "response.output_audio_transcript.done",
                "transcript": f"proof-reply-{turn}",
            }
        )
        self.emit({"type": "response.done", "status": "completed"})
