"""Beam.cloud @asgi OpenVoice voice-changer worker (CPU-only).

Exposes an OpenAI Realtime-compatible WebSocket at ``/v1/realtime``. Instead of
transcribing/answering, it captures the user's speech turn (via Silero VAD),
re-voices it into a target reference speaker with OpenVoice, and streams the
converted PCM16 audio straight back. The chosen voice comes from the client
``session.update`` event (``session.voice``), defaulting to ``GutAI``.

No GPU, no model downloads at runtime — the converter checkpoint ships inside
the ``openvoice-cli`` package and the target voices are committed in
``voices/reference_voices/``.
"""

from __future__ import annotations

import asyncio
import base64
import time
import uuid

from beam import Image, QueueDepthAutoscaler, asgi
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# NOTE: `workers.voice.handlers`/`workers.voice.realtime` ship with the
# worker directory. Imports stay function-deferred (same pattern as the
# qwen worker) so the module imports cleanly locally and the fake
# harness can stub at the loader boundary.

INPUT_SR = 24000
VAD_SR = 16000
CHUNK_BYTES = 4096

image = (
    Image(python_version="python3.11")
    .add_python_packages(
        [
            "fastapi",
            "uvicorn[standard]",
            "numpy",
            "soundfile",
            "openvoice-cli",
            "librosa==0.9.1",
            "setuptools==80.9.0",
            "torch",
            "torchaudio",
        ]
    )
)


def load_converter():
    from workers.voice.handlers.voice_converter import VoiceConverter

    t0 = time.time()
    converter = VoiceConverter(device="cpu", watermark=False).load()
    print(f"[INIT] OpenVoice converter ready in {time.time() - t0:.1f}s")
    return converter


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _default_voice() -> str:
    from workers.voice.handlers.voice_converter import DEFAULT_VOICE

    return DEFAULT_VOICE


class OpenVoiceSession:
    def __init__(self, converter, send, default_voice: str | None = None) -> None:
        from workers.voice.realtime.vad import SileroVAD

        self._converter = converter
        self._send = send
        self._loop: asyncio.AbstractEventLoop | None = None
        self._voice = default_voice or _default_voice()
        self._vad = SileroVAD().load()
        self._in_turn = False
        self._turn_audio = bytearray()
        self._active_turn: asyncio.Task | None = None

    async def handle_message(self, raw: str) -> None:
        from workers.voice.realtime.protocol import Event

        if self._loop is None:
            self._loop = asyncio.get_running_loop()
        try:
            ev = Event.from_json(raw)
        except Exception as exc:  # noqa: BLE001
            await self._emit(Event.error_event(f"malformed event: {exc}"))
            return

        t = ev.type
        if t == "input_audio_buffer.append":
            await self._on_audio(ev.data.get("audio", ""))
        elif t == "input_audio_buffer.commit":
            pass  # client signals end of an audio turn; we auto-trigger on VAD
        elif t == "session.update":
            await self._apply_session(ev.data.get("session", {}))
        elif t == "response.cancel":
            if self._active_turn:
                self._active_turn.cancel()
        else:
            await self._emit(Event.error_event(f"unsupported event: {t}"))

    async def close(self) -> None:
        if self._active_turn:
            self._active_turn.cancel()

    async def start(self) -> None:
        from workers.voice.realtime.protocol import Event

        await self._emit(
            Event.session_created(
                {"id": "session_1", "voice": self._voice, "modalities": ["audio"]}
            )
        )

    # -- session config (voice selection) ---------------------------------
    async def _apply_session(self, session: dict) -> None:
        from workers.voice.realtime.protocol import Event
        # OpenWebUI (gpt-realtime fork) sends the selected voice as
        # session.voice; tolerate a few layouts just in case.
        voice = (
            session.get("voice")
            or session.get("output", {}).get("voice")
            or session.get("turn_detection", {}).get("voice")
        )
        if voice and voice in self._converter.voices():
            self._voice = voice
        await self._emit(
            Event.session_updated({"id": "session_1", "voice": self._voice})
        )

    # -- inbound audio / VAD ----------------------------------------------
    async def _on_audio(self, audio_b64: str) -> None:
        from workers.voice.realtime.audio import resample_pcm16
        from workers.voice.realtime.protocol import Event

        if not audio_b64:
            return
        pcm24 = base64.b64decode(audio_b64)
        pcm16_16k = resample_pcm16(pcm24, INPUT_SR, VAD_SR)

        status = await self._loop.run_in_executor(  # type: ignore[union-attr]
            None, self._vad.feed, pcm16_16k
        )
        if status["speech_started"]:
            self._in_turn = True
            self._turn_audio = bytearray()
            await self._emit(Event.speech_started())
        if self._in_turn:
            self._turn_audio += pcm24
        if status["speech_stopped"] and self._in_turn:
            self._in_turn = False
            captured = bytes(self._turn_audio)
            self._turn_audio = bytearray()
            await self._emit(Event.speech_stopped())
            self._active_turn = asyncio.create_task(self._convert_turn(captured))

    # -- convert + stream -------------------------------------------------
    async def _convert_turn(self, audio24k: bytes) -> None:
        from workers.voice.realtime.protocol import Event

        response_id = _new_id("resp")
        item_id = _new_id("item")
        await self._emit(
            Event.response_created({"id": response_id, "status": "in_progress"})
        )
        try:
            out_pcm = await self._loop.run_in_executor(  # type: ignore[union-attr]
                None, self._converter.convert, audio24k, self._voice
            )
        except Exception as exc:  # noqa: BLE001
            await self._emit(Event.error_event(f"conversion failed: {exc}"))
            return

        for i in range(0, len(out_pcm), CHUNK_BYTES):
            await self._emit(
                Event.response_audio_delta(
                    base64.b64encode(out_pcm[i : i + CHUNK_BYTES]).decode("ascii"),
                    item_id=item_id,
                    response_id=response_id,
                )
            )
        await self._emit(
            Event.response_done({"id": response_id, "status": "completed"})
        )

    async def _emit(self, ev) -> None:
        await self._send(ev.to_json())


@asgi(
    name="voice-openvoice",
    image=image,
    on_start=load_converter,
    gpu=None,
    cpu=2,
    memory="4Gi",
    concurrent_requests=4,
    keep_warm_seconds=10,
    timeout=-1,
    authorized=True,
    autoscaler=QueueDepthAutoscaler(max_containers=4, min_containers=0),
)
def worker(context):
    converter = context.on_start_value
    app = FastAPI()

    @app.websocket("/v1/realtime")
    async def realtime_ws(websocket: WebSocket):
        await websocket.accept()
        session = OpenVoiceSession(converter, send=websocket.send_text)
        await session.start()
        try:
            while True:
                raw = await websocket.receive_text()
                await session.handle_message(raw)
        except WebSocketDisconnect:
            await session.close()
        except Exception:  # noqa: BLE001
            await session.close()

    return app
