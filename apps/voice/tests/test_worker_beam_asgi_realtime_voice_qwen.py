import json

from fastapi.testclient import TestClient

import apps.voice.worker_beam_asgi_realtime_voice_qwen as worker_mod


class FakeVAD:
    def feed(self, pcm16_16k):
        return {"speech_started": False, "speech_stopped": False}


class FakeSTT:
    last_language = "en"

    def transcribe(self, audio24k):
        return "hello world"


class FakeLLM:
    def stream(self, messages, cancel=None):
        yield "Hello"
        yield " world"


class FakeTTS:
    def stream(self, transcript, voice=None, cancel=None):
        yield b"\x00\x00" * 8


def _models():
    return {"vad": FakeVAD(), "stt": FakeSTT(), "llm": FakeLLM(), "tts": FakeTTS()}


def _ws_client():
    app = worker_mod.build_app(_models(), None)
    return TestClient(app)


def test_connect_emits_session_created():
    with _ws_client() as client, client.websocket_connect("/v1/realtime") as ws:
        ev = json.loads(ws.receive_text())
        assert ev["type"] == "session.created"


def test_session_update_echoes_voice():
    with _ws_client() as client, client.websocket_connect("/v1/realtime") as ws:
        ws.receive_text()  # session.created
        ws.send_text(
            json.dumps({"type": "session.update", "session": {"voice": "Bob"}})
        )
        ev = json.loads(ws.receive_text())
        assert ev["type"] == "session.updated"
        assert ev["session"]["voice"] == "Bob"


def test_malformed_json_returns_error():
    with _ws_client() as client, client.websocket_connect("/v1/realtime") as ws:
        ws.receive_text()  # session.created
        ws.send_text("not json")
        ev = json.loads(ws.receive_text())
        assert ev["type"] == "error"


def test_text_turn_streams_response():
    with _ws_client() as client, client.websocket_connect("/v1/realtime") as ws:
        ws.receive_text()  # session.created
        ws.send_text(
            json.dumps(
                {
                    "type": "conversation.item.create",
                    "item": {
                        "type": "message",
                        "content": [{"type": "input_text", "text": "hi"}],
                    },
                }
            )
        )
        ws.send_text(json.dumps({"type": "response.create"}))
        types = []
        for _ in range(6):
            ev = json.loads(ws.receive_text())
            types.append(ev["type"])
        assert "response.created" in types
        assert "response.audio_transcript.delta" in types
        assert "response.audio.delta" in types
        assert "response.done" in types

