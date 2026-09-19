"""Per-connection Realtime session state machine.

Owns the inbound audio buffer, drives the VAD -> STT -> LLM -> TTS cascade,
and emits outbound events through an injected ``send`` callable (the WebSocket
``send_text`` in the worker entrypoints).

Heavy model calls run in worker threads (via the loop's default executor) so
the WebSocket event loop stays free to receive ``response.cancel`` for
barge-in. Events produced on those threads are pushed back onto the async
loop through the queue consumed in ``_run_pipeline``.
"""

from __future__ import annotations

import asyncio
import base64
import uuid

from apps.gpu_workers.voice.handlers.voices_config import persona_for
from apps.gpu_workers.voice.realtime.audio import resample_pcm16
from apps.gpu_workers.voice.realtime.protocol import Event

INPUT_SR = 24000
VAD_SR = 16000
SYSTEM_PROMPT = (
    "You are a helpful, concise voice assistant. Keep replies short and "
    "conversational; avoid long monologues."
)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class Session:
    def __init__(self, models: dict, send, voices_config: dict | None = None, default_voice: str = "GutAI") -> None:
        self._models = models
        self._send = send
        self._voices_config = voices_config
        self._default_voice = default_voice
        self._voice = default_voice
        self._last_language: str | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

        persona = (
            persona_for(self._voices_config, default_voice, default_voice)
            if self._voices_config
            else SYSTEM_PROMPT
        )
        self._history: list[dict] = [{"role": "system", "content": persona}]
        self._pending_text: str | None = None

        self._in_turn = False
        self._turn_audio = bytearray()
        self._active_turn: asyncio.Task | asyncio.Future | None = None
        self._cancel_event: asyncio.Event | None = None

    # -- public API -------------------------------------------------------
    async def handle_message(self, raw: str) -> None:
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
        elif t == "conversation.item.create":
            self._on_item_create(ev.data.get("item", {}))
        elif t == "response.create":
            await self._on_response_create()
        elif t == "response.cancel":
            await self._on_response_cancel(ev.data.get("response_id"))
        else:
            await self._emit(Event.error_event(f"unsupported event: {t}"))

    async def close(self) -> None:
        if self._cancel_event:
            self._cancel_event.set()
        if self._active_turn:
            self._active_turn.cancel()

    async def start(self) -> None:
        instructions = (
            self._history[0]["content"]
            if self._history and self._history[0].get("role") == "system"
            else ""
        )
        await self._emit(
            Event.session_created(
                {
                    "id": "session_1",
                    "model": "voice-worker",
                    "voice": self._voice,
                    "modalities": ["text", "audio"],
                    "instructions": instructions,
                }
            )
        )

    # -- session config (voice + persona) --------------------------------
    async def _apply_session(self, session: dict) -> None:
        # Tolerant parse of the selected voice across client layouts.
        voice = (
            session.get("voice")
            or session.get("output", {}).get("voice")
            or session.get("turn_detection", {}).get("voice")
        )
        if voice:
            self.set_voice(voice)
        await self._emit(
            Event.session_updated({"id": "session_1", "voice": self._voice})
        )

    def set_voice(self, voice: str) -> None:
        if not voice:
            return
        self._voice = voice
        persona = (
            persona_for(self._voices_config, voice, self._default_voice)
            if self._voices_config
            else SYSTEM_PROMPT
        )
        if self._history and self._history[0].get("role") == "system":
            self._history[0]["content"] = persona
        else:
            self._history.insert(0, {"role": "system", "content": persona})

    # -- inbound handlers -------------------------------------------------
    async def _on_audio(self, audio_b64: str) -> None:
        if not audio_b64:
            return
        pcm24 = base64.b64decode(audio_b64)
        pcm16_16k = resample_pcm16(pcm24, INPUT_SR, VAD_SR)

        assert self._loop is not None
        status = await self._loop.run_in_executor(
            None, self._models["vad"].feed, pcm16_16k
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
            self._active_turn = asyncio.create_task(self._audio_turn(captured))

    def _on_item_create(self, item: dict) -> None:
        # Support text turns (used by the smoke test and Realtime clients that
        # send text items instead of audio).
        if item.get("type") != "message":
            return
        for part in item.get("content", []):
            if part.get("type") == "input_text":
                self._pending_text = part.get("text", "")
                return

    async def _on_response_create(self) -> None:
        if self._pending_text:
            text = self._pending_text
            self._pending_text = None
            self._active_turn = asyncio.create_task(self._text_turn(text))

    async def _on_response_cancel(self, response_id: str | None) -> None:
        if self._cancel_event:
            self._cancel_event.set()
        if self._active_turn:
            self._active_turn.cancel()
            self._active_turn = None
        await self._emit(
            Event.response_done({"id": response_id or "", "status": "cancelled"})
        )

    # -- turn pipelines ---------------------------------------------------
    async def _audio_turn(self, audio24k: bytes) -> None:
        try:
            assert self._loop is not None
            text = await self._loop.run_in_executor(
                None, self._models["stt"].transcribe, audio24k
            )
            self._last_language = getattr(
                self._models["stt"], "last_language", None
            )
            if not text.strip():
                return
            await self._respond(text)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            await self._emit(Event.error_event(f"transcription failed: {exc}"))

    async def _text_turn(self, text: str) -> None:
        await self._respond(text)

    async def _respond(self, user_text: str) -> None:
        self._history.append({"role": "user", "content": user_text})
        response_id = _new_id("resp")
        item_id = _new_id("item")
        self._cancel_event = asyncio.Event()
        await self._emit(
            Event.response_created({"id": response_id, "status": "in_progress"})
        )
        await self._run_pipeline(list(self._history), response_id, item_id)

    async def _run_pipeline(
        self, messages: list[dict], response_id: str, item_id: str
    ) -> None:
        queue: asyncio.Queue = asyncio.Queue()
        cancel = self._cancel_event
        loop = self._loop
        assert loop is not None

        def worker() -> None:
            try:
                full: list[str] = []
                for token in self._models["llm"].stream(messages, cancel=cancel):
                    full.append(token)
                    loop.call_soon_threadsafe(
                        queue.put_nowait, ("transcript", "".join(full))
                    )
                transcript = "".join(full)
                loop.call_soon_threadsafe(
                    queue.put_nowait, ("transcript_done", transcript)
                )
                # Language-aware TTS routing: Chatterbox (reference timbre)
                # for English; QwenTTS fallback (multilingual) for non-English.
                use_fallback = bool(
                    self._last_language
                    and self._last_language != "en"
                    and self._models.get("tts_fallback") is not None
                )
                if use_fallback:
                    tts = self._models["tts_fallback"]
                    chunks = tts.stream(transcript, cancel=cancel)
                else:
                    tts = self._models["tts"]
                    chunks = tts.stream(transcript, self._voice, cancel=cancel)
                for audio_pcm16 in chunks:
                    loop.call_soon_threadsafe(
                        queue.put_nowait,
                        ("audio", base64.b64encode(audio_pcm16).decode("ascii")),
                    )
                if cancel is not None and cancel.is_set():
                    loop.call_soon_threadsafe(queue.put_nowait, ("cancelled", None))
                else:
                    loop.call_soon_threadsafe(queue.put_nowait, ("done", None))
            except Exception as exc:  # noqa: BLE001
                loop.call_soon_threadsafe(queue.put_nowait, ("error", exc))

        task = loop.run_in_executor(None, worker)
        self._active_turn = asyncio.wrap_future(task)  # track for cancel
        try:
            while True:
                kind, payload = await queue.get()
                if kind == "transcript":
                    await self._emit(
                        Event.response_audio_transcript_delta(
                            payload, item_id=item_id, response_id=response_id
                        )
                    )
                elif kind == "transcript_done":
                    self._history.append({"role": "assistant", "content": payload})
                    await self._emit(
                        Event.response_audio_transcript_done(
                            payload, item_id=item_id, response_id=response_id
                        )
                    )
                elif kind == "audio":
                    await self._emit(
                        Event.response_audio_delta(
                            payload, item_id=item_id, response_id=response_id
                        )
                    )
                elif kind == "done":
                    await self._emit(
                        Event.response_done(
                            {"id": response_id, "status": "completed"}
                        )
                    )
                    break
                elif kind == "cancelled":
                    await self._emit(
                        Event.response_done(
                            {"id": response_id, "status": "cancelled"}
                        )
                    )
                    break
                elif kind == "error":
                    await self._emit(
                        Event.error_event(f"generation failed: {payload}")
                    )
                    break
        except asyncio.CancelledError:
            if cancel:
                cancel.set()
            raise
        finally:
            self._active_turn = None

    # -- helpers ----------------------------------------------------------
    async def _emit(self, ev: Event) -> None:
        await self._send(ev.to_json())
