import base64
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import workers.voice.worker_beam_asgi_realtime_voice_chatterbox as worker_mod


class FakeTTS:
    def voices(self):
        return ["GutAI"]

    def generate(self, text, voice="GutAI"):
        assert text == "hi"
        assert voice == "GutAI"
        return b"\x01\x02" * 12000


def _app():
    ctx = SimpleNamespace(on_start_value=FakeTTS())
    # .local runs the raw function; the decorator blocks direct calls.
    return worker_mod.worker.local(ctx)


@pytest.mark.local_e2e
def test_e2e_chatterbox_lists_voices():
    out = TestClient(_app()).get("/v1/audio/voices").json()

    assert out == {"voices": [{"id": "GutAI", "name": "GutAI"}]}


@pytest.mark.local_e2e
def test_e2e_chatterbox_returns_wav_audio():
    resp = TestClient(_app()).post(
        "/v1/audio/speech", json={"model": "tts", "input": "hi", "voice": "GutAI"}
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/wav"
    assert resp.content[:4] == b"RIFF"


def test_pcm_to_wav_wraps_bytes():
    out = worker_mod._pcm_to_wav(b"\x01\x02", 24000)

    assert out[:4] == b"RIFF"
    assert out.endswith(b"\x01\x02")
    assert base64.b64encode(out) != b""
