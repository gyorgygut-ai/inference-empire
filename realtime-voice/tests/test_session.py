"""Session state-machine tests using stub handlers (no GPU / models needed).

Drives a text turn through the full VAD-less path and asserts the outbound
event sequence: response.created -> transcript deltas -> audio deltas ->
response.done. Barge-in (response.cancel) is also exercised.
"""

from __future__ import annotations

import asyncio

import pytest

realtime = pytest.importorskip("realtime")
from realtime.protocol import Event  # noqa: E402
from realtime.session import Session  # noqa: E402


class StubSTT:
    def transcribe(self, pcm24):
        return "transcribed audio"


class StubLLM:
    def stream(self, messages, cancel=None, max_new_tokens=None):
        import time

        for tok in ["Hello", " world", "!"]:
            if cancel is not None and cancel.is_set():
                break
            time.sleep(0.03)  # slow enough for barge-in to land mid-turn
            yield tok


class StubTTS:
    def stream(self, text, voice=None, cancel=None, chunk_size=8):
        import time

        self.last_voice = voice
        for _ in range(3):
            if cancel is not None and cancel.is_set():
                break
            time.sleep(0.03)
            yield b"\x00\x01" * 50  # fake 16-bit PCM samples


class StubVAD:
    def feed(self, pcm16_16k):
        return {"speech_started": False, "speech_stopped": False}


def _models():
    return {"stt": StubSTT(), "llm": StubLLM(), "tts": StubTTS(), "vad": StubVAD()}


class Collector:
    def __init__(self):
        self.events: list[Event] = []

    async def send(self, text):
        self.events.append(Event.from_json(text))


async def _drain(session: Session, collector: Collector, timeout: float = 2.0):
    # Let any background tasks / executor threads flush their events.
    step = 0.02
    elapsed = 0.0
    while elapsed < timeout:
        await asyncio.sleep(step)
        elapsed += step
        if any(e.type == "response.done" for e in collector.events):
            # allow trailing audio deltas to land before we check
            await asyncio.sleep(step * 3)
            return


async def test_text_turn_emits_expected_sequence():
    collector = Collector()
    session = Session(_models(), send=collector.send)

    await session.handle_message(Event.session_update({"turn_detection": {"type": "none"}}).to_json())
    await session.handle_message(
        Event.conversation_item_create(
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "hi"}],
            }
        ).to_json()
    )
    await session.handle_message(Event.response_create().to_json())

    await _drain(session, collector)

    types = [e.type for e in collector.events]
    assert "response.created" in types
    assert "response.audio_transcript.delta" in types
    assert "response.audio_transcript.done" in types
    assert "response.audio.delta" in types
    assert "response.done" in types
    assert "error" not in types

    done = next(e for e in collector.events if e.type == "response.done")
    assert done.data["response"]["status"] == "completed"


async def test_barge_in_cancels_turn():
    collector = Collector()
    session = Session(_models(), send=collector.send)

    await session.handle_message(
        Event.conversation_item_create(
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "hi"}],
            }
        ).to_json()
    )
    await session.handle_message(Event.response_create().to_json())
    await asyncio.sleep(0.05)
    await session.handle_message(Event.response_cancel().to_json())

    await _drain(session, collector, timeout=1.0)
    types = [e.type for e in collector.events]
    assert "response.done" in types
    done = next(e for e in collector.events if e.type == "response.done")
    assert done.data["response"]["status"] == "cancelled"


VOICE_CFG = {
    "default_voice": "GutAI",
    "voices": {
        "GutAI": {"file": "GutAI.wav", "persona": "P-GutAI"},
        "ff": {"file": "ff.wav", "persona": "P-ff"},
    },
}


async def test_voice_switch_updates_persona_and_tts_voice():
    collector = Collector()
    session = Session(
        _models(), send=collector.send, voices_config=VOICE_CFG, default_voice="GutAI"
    )
    assert session._history[0]["content"] == "P-GutAI"

    await session.handle_message(Event.session_update({"voice": "ff"}).to_json())
    assert session._voice == "ff"
    assert session._history[0]["content"] == "P-ff"

    await session.handle_message(
        Event.conversation_item_create(
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "hi"}],
            }
        ).to_json()
    )
    await session.handle_message(Event.response_create().to_json())
    await _drain(session, collector)

    assert session._models["tts"].last_voice == "ff"


async def test_unknown_voice_keeps_default():
    collector = Collector()
    session = Session(
        _models(), send=collector.send, voices_config=VOICE_CFG, default_voice="GutAI"
    )
    await session.handle_message(Event.session_update({"voice": "does-not-exist"}).to_json())
    assert session._voice == "does-not-exist"  # accepted, timbre requested as-is
    assert session._history[0]["content"] == "P-GutAI"  # persona falls back to default
