import asyncio

from workers.voice.realtime.protocol import Event
from workers.voice.realtime.session import Session


class FakeVAD:
    def __init__(self, script):
        self._script = list(script)

    def feed(self, audio):
        return self._script.pop(0)


class FakeSTT:
    last_language = "en"

    def transcribe(self, audio):
        return "hello"


class FakeLLM:
    def stream(self, messages, cancel=None):
        yield "hi"


class FakeTTS:
    def stream(self, transcript, voice, cancel=None):
        assert transcript == "hi"
        yield b"\x00\x00" * 100


def _session(statuses=None):
    sent = []
    models = {
        "vad": FakeVAD(statuses or []),
        "stt": FakeSTT(),
        "llm": FakeLLM(),
        "tts": FakeTTS(),
    }

    async def send(text):
        sent.append(text)

    return Session(models, send), sent


def _run(coro):
    return asyncio.run(coro)


def _types(sent):
    return [Event.from_json(raw).type for raw in sent]


def test_start_emits_session_created():
    session, sent = _session()

    async def main():
        await session.start()

    _run(main())

    assert _types(sent) == ["session.created"]


def test_session_update_returns_updated_voice():
    session, sent = _session()

    async def main():
        await session.handle_message(Event.session_update({"voice": "bo"}).to_json())

    _run(main())

    ev = Event.from_json(sent[-1])
    assert ev.type == "session.updated"
    assert ev.data["session"]["voice"] == "bo"


def test_malformed_event_returns_error():
    session, sent = _session()

    async def main():
        await session.handle_message("not json")

    _run(main())

    assert _types(sent) == ["error"]


def test_text_turn_returns_transcript_audio_and_done():
    session, sent = _session()

    async def main():
        await session.handle_message(
            Event.conversation_item_create(
                {"type": "message", "content": [{"type": "input_text", "text": "hi"}]}
            ).to_json()
        )
        await session.handle_message(Event.response_create().to_json())
        await asyncio.sleep(0.5)

    _run(main())

    types = _types(sent)
    assert "response.created" in types
    assert "response.audio_transcript.done" in types
    assert "response.audio.delta" in types
    assert types[-1] == "response.done"


def test_response_cancel_returns_cancelled_done():
    session, sent = _session()

    async def main():
        await session.handle_message(Event.response_cancel("resp_1").to_json())

    _run(main())

    ev = Event.from_json(sent[-1])
    assert ev.type == "response.done"
    assert ev.data["response"]["status"] == "cancelled"
