import base64
import time
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

import workers.voice.realtime.vad as vad_mod
import workers.voice.worker_beam_asgi_realtime_voice_openvoice as worker_mod
from workers.voice.realtime.protocol import Event


class FakeConverter:
    def voices(self):
        return ["GutAI"]

    def convert(self, audio, voice):
        assert voice == "GutAI"
        return b"\x03\x04" * 500


class FakeVAD:
    def __init__(self, script):
        self._script = list(script)

    def load(self):
        return self

    def feed(self, audio):
        return self._script.pop(0)


def _client(monkeypatch):
    monkeypatch.setattr(
        vad_mod,
        "SileroVAD",
        lambda *a, **k: FakeVAD(
            [
                {"speech_started": True, "speech_stopped": False},
                {"speech_started": False, "speech_stopped": True},
            ]
        ),
    )
    ctx = SimpleNamespace(on_start_value=FakeConverter())
    # .local runs the raw function; the decorator blocks direct calls.
    return TestClient(worker_mod.worker.local(ctx))


def _audio_b64():
    return base64.b64encode(np.zeros(2048, dtype=np.int16).tobytes()).decode("ascii")


@pytest.mark.local_e2e
def test_e2e_openvoice_session_update_returns_updated_session(monkeypatch):
    with _client(monkeypatch).websocket_connect("/v1/realtime") as ws:
        assert Event.from_json(ws.receive_text()).type == "session.created"
        ws.send_text(Event.session_update({"voice": "GutAI"}).to_json())

        out = Event.from_json(ws.receive_text())

    assert out.type == "session.updated"
    assert out.data["session"]["voice"] == "GutAI"


@pytest.mark.local_e2e
def test_e2e_openvoice_speech_turn_returns_converted_audio(monkeypatch):
    deltas = []

    with _client(monkeypatch).websocket_connect("/v1/realtime") as ws:
        assert Event.from_json(ws.receive_text()).type == "session.created"
        ws.send_text(Event.input_audio_append(_audio_b64()).to_json())
        assert Event.from_json(ws.receive_text()).type == "input_audio_buffer.speech_started"
        ws.send_text(Event.input_audio_append(_audio_b64()).to_json())
        for _ in range(6):
            ev = Event.from_json(ws.receive_text())
            if ev.type == "response.audio.delta":
                deltas.append(ev.data["delta"])
            if ev.type == "response.done":
                break
        time.sleep(0.2)

    assert deltas, "no converted audio streamed back"
    assert base64.b64decode(deltas[0]) == b"\x03\x04" * 500


@pytest.mark.local_e2e
def test_e2e_openvoice_rejects_malformed_event(monkeypatch):
    with _client(monkeypatch).websocket_connect("/v1/realtime") as ws:
        ws.receive_text()
        ws.send_text("not json")

        out = Event.from_json(ws.receive_text())

    assert out.type == "error"


def test_new_id_format():
    assert worker_mod._new_id("resp").startswith("resp_")
