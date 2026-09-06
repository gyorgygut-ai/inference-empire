import base64
import time
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

import workers.voice.worker_beam_asgi_realtime_voice_qwen as worker_mod
from workers.voice.realtime.protocol import Event


class FakeVAD:
    def feed(self, audio):
        return {"speech_started": True, "speech_stopped": True}


class FakeSTT:
    last_language = "en"

    def transcribe(self, audio):
        return "hello"


class FakeLLM:
    def stream(self, messages, cancel=None):
        assert messages[0]["role"] == "system"
        yield "hi"


class FakeTTS:
    def stream(self, transcript, voice, cancel=None):
        assert transcript == "hi"
        yield b"\x05\x06" * 500


def _client():
    models = {
        "tts": FakeTTS(),
        "stt": FakeSTT(),
        "llm": FakeLLM(),
        "vad": FakeVAD(),
    }
    ctx = SimpleNamespace(on_start_value=models)
    # .local runs the raw function; the decorator blocks direct calls.
    return TestClient(worker_mod.worker.local(ctx))


def _audio_b64():
    return base64.b64encode(np.zeros(2048, dtype=np.int16).tobytes()).decode("ascii")


@pytest.mark.local_e2e
def test_e2e_qwen_text_turn_returns_transcript_and_audio():
    with _client().websocket_connect("/v1/realtime") as ws:
        assert Event.from_json(ws.receive_text()).type == "session.created"
        ws.send_text(
            Event.conversation_item_create(
                {"type": "message", "content": [{"type": "input_text", "text": "hi"}]}
            ).to_json()
        )
        ws.send_text(Event.response_create().to_json())

        types = [Event.from_json(ws.receive_text()).type for _ in range(5)]

    assert "response.created" in types
    assert "response.audio_transcript.done" in types
    assert "response.audio.delta" in types
    assert "response.done" in types


@pytest.mark.local_e2e
def test_e2e_qwen_audio_turn_returns_answer():
    with _client().websocket_connect("/v1/realtime") as ws:
        assert Event.from_json(ws.receive_text()).type == "session.created"
        ws.send_text(Event.input_audio_append(_audio_b64()).to_json())

        types = [Event.from_json(ws.receive_text()).type for _ in range(7)]
        time.sleep(0.2)

    assert "input_audio_buffer.speech_started" in types
    assert "input_audio_buffer.speech_stopped" in types
    assert "response.done" in types
