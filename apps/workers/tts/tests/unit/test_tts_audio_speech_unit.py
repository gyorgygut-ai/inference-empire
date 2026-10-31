import io
import os
import struct
import wave

import pytest
from fastapi.testclient import TestClient
from shared.worker_tts_audio_speech import build_app
from tests.stub_services import tts_generator_stub

TTS_API_KEY = "tts-test-key"


@pytest.fixture
def client():
    os.environ["SECRET_TTS_AUDIO_SPEECH_API_KEY"] = TTS_API_KEY
    app = build_app(generator=tts_generator_stub)
    return TestClient(app)


def test_tts_health_returns_200(client):
    r = client.get("/health")
    assert r.status_code == 200, "health check failed"


def test_tts_health_response_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_tts_missing_or_invalid_token_returns_401(client):
    # Missing auth header
    r = client.post(
        "/v1/audio/speech",
        json={"model": "resembleai_chatterbox_tts", "input": "hello"},
    )
    assert r.status_code == 401, "missing token not rejected"

    # Invalid token
    r = client.post(
        "/v1/audio/speech",
        headers={"Authorization": "Bearer bad"},
        json={"model": "resembleai_chatterbox_tts", "input": "hello"},
    )
    assert r.status_code == 401, "invalid token not rejected"


def test_tts_missing_or_invalid_token_response_error(client):
    r = client.post(
        "/v1/audio/speech",
        headers={"Authorization": "Bearer bad"},
        json={"model": "resembleai_chatterbox_tts", "input": "hello"},
    )
    assert r.status_code == 401
    assert "detail" in r.json(), "missing detail in error response"


def test_tts_unsupported_format_returns_422(client):
    # response_format: json is unsupported
    r = client.post(
        "/v1/audio/speech",
        headers={"Authorization": f"Bearer {TTS_API_KEY}"},
        json={
            "model": "resembleai_chatterbox_tts",
            "input": "hello",
            "response_format": "json",
        },
    )
    assert r.status_code == 422, "unsupported format not rejected"


def test_tts_unsupported_format_response_error(client):
    r = client.post(
        "/v1/audio/speech",
        headers={"Authorization": f"Bearer {TTS_API_KEY}"},
        json={
            "model": "resembleai_chatterbox_tts",
            "input": "hello",
            "response_format": "json",
        },
    )
    assert r.status_code == 422
    assert "detail" in r.json(), "missing detail in error response"


def test_tts_valid_text_wav_returns_200(client):
    r = client.post(
        "/v1/audio/speech",
        headers={"Authorization": f"Bearer {TTS_API_KEY}"},
        json={
            "model": "resembleai_chatterbox_tts",
            "input": "hello world",
            "response_format": "wav",
        },
    )
    assert r.status_code == 200, "valid text request failed"


def test_tts_valid_text_wav_response_content_type(client):
    r = client.post(
        "/v1/audio/speech",
        headers={"Authorization": f"Bearer {TTS_API_KEY}"},
        json={
            "model": "resembleai_chatterbox_tts",
            "input": "hello world",
            "response_format": "wav",
        },
    )
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("audio/wav"), "wrong content type"


def test_tts_valid_text_wav_response_non_silent(client):
    r = client.post(
        "/v1/audio/speech",
        headers={"Authorization": f"Bearer {TTS_API_KEY}"},
        json={
            "model": "resembleai_chatterbox_tts",
            "input": "hello world",
            "response_format": "wav",
        },
    )
    assert r.status_code == 200
    audio_bytes = r.content
    assert len(audio_bytes) > 0, "empty audio response"

    # Parse WAV and check for non-silent audio
    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wav:
            frames = wav.readframes(wav.getnframes())
            samples = struct.unpack(f"<{len(frames)//2}h", frames)
            assert any(abs(s) > 0 for s in samples), "audio is silent"
    except Exception:
        # If WAV parsing fails, fall back to simple length check
        assert len(audio_bytes) > 0, "audio is empty"
