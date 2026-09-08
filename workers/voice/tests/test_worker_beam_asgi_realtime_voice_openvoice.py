import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

import workers.voice.worker_beam_asgi_realtime_voice_openvoice as worker_mod


class FakeVAD:
    def load(self):
        return self

    def feed(self, pcm16_16k):
        return {"speech_started": False, "speech_stopped": False}


class FakeConverter:
    def voices(self):
        return ["Bob", "GutAI"]

    def convert(self, audio24k, voice):
        return b"\x00\x00" * 100


def _app(monkeypatch):
    monkeypatch.setattr("workers.voice.realtime.vad.SileroVAD", FakeVAD)
    ctx = SimpleNamespace(on_start_value=FakeConverter())
    return worker_mod.worker.local(ctx)


def test_connect_emits_session_created(monkeypatch):
    app = _app(monkeypatch)
    with TestClient(app) as client:
        with client.websocket_connect("/v1/realtime") as ws:
            ev = json.loads(ws.receive_text())
            assert ev["type"] == "session.created"


def test_session_update_echoes_voice(monkeypatch):
    app = _app(monkeypatch)
    with TestClient(app) as client:
        with client.websocket_connect("/v1/realtime") as ws:
            ws.receive_text()  # session.created
            ws.send_text(
                json.dumps({"type": "session.update", "session": {"voice": "Bob"}})
            )
            ev = json.loads(ws.receive_text())
            assert ev["type"] == "session.updated"
            assert ev["session"]["voice"] == "Bob"


def test_malformed_json_returns_error(monkeypatch):
    app = _app(monkeypatch)
    with TestClient(app) as client:
        with client.websocket_connect("/v1/realtime") as ws:
            ws.receive_text()  # session.created
            ws.send_text("garbage")
            ev = json.loads(ws.receive_text())
            assert ev["type"] == "error"