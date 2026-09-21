import io
import wave
from types import SimpleNamespace

from fastapi.testclient import TestClient

import apps.gpu_workers.voice.worker_beam_asgi_realtime_voice_chatterbox as worker_mod


class FakeChatterbox:
    def voices(self):
        return ["Bob", "GutAI"]

    def generate(self, text, voice="GutAI"):
        return b"\x00\x00" * 100


def _app():
    ctx = SimpleNamespace(on_start_value=FakeChatterbox())
    return worker_mod.worker.local(ctx)


def test_list_voices():
    app = _app()
    with TestClient(app) as client:
        r = client.get("/v1/audio/voices")
        assert r.status_code == 200
        assert r.json() == {
            "voices": [
                {"id": "Bob", "name": "Bob"},
                {"id": "GutAI", "name": "GutAI"},
            ]
        }


def test_speech_returns_wav():
    app = _app()
    with TestClient(app) as client:
        r = client.post(
            "/v1/audio/speech", json={"input": "hello", "voice": "Bob"}
        )
        assert r.status_code == 200
        assert r.headers["content-type"] == "audio/wav"
        with wave.open(io.BytesIO(r.content)) as w:
            assert w.getframerate() == 24000
            assert len(w.readframes(w.getnframes())) > 0