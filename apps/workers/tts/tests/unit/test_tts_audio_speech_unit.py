import base64
import io
import os
import wave

import numpy as np
import pytest
from dist.contract_tts_audio_speech import Output
from fastapi.testclient import TestClient
from shared.worker_tts_audio_speech import build_app, encode_audio
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


def test_tts_response_contains_inline_audio_base64(client):
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
    assert r.headers.get("content-type", "").startswith("application/json")
    assert isinstance(r.json().get("audio_base64"), str)


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
    audio_bytes = base64.b64decode(r.json()["audio_base64"], validate=True)
    assert len(audio_bytes) > 0, "empty audio response"

    with wave.open(io.BytesIO(audio_bytes), "rb") as wav:
        assert wav.getframerate() == 24_000
        assert wav.getnchannels() == 1
        frames = wav.readframes(wav.getnframes())
        assert any(frames), "audio is silent"


def test_tts_encode_audio_normalizes_to_mono_24khz():
    result = encode_audio(np.ones((2, 1600), dtype=np.float32) * 0.25, 16_000)
    audio_bytes = base64.b64decode(result.audio_base64, validate=True)
    with wave.open(io.BytesIO(audio_bytes), "rb") as wav:
        assert result.sample_rate == wav.getframerate() == 24_000
        assert wav.getnchannels() == 1
        assert wav.getnframes() == 2400


def test_tts_encode_audio_rejects_silence():
    with pytest.raises(ValueError, match="silent"):
        encode_audio(np.zeros(100, dtype=np.float32), 24_000)


def test_tts_endpoint_rejects_malformed_wav():
    def malformed_generator(_request) -> Output:
        return Output(
            format="wav",
            audio_base64=base64.b64encode(b"not wav").decode("ascii"),
            sample_rate=24_000,
        )

    app = build_app(generator=malformed_generator, api_key=TTS_API_KEY)
    with TestClient(app) as client:
        response = client.post(
            "/v1/audio/speech",
            headers={"Authorization": f"Bearer {TTS_API_KEY}"},
            json={
                "model": "resembleai_chatterbox_tts",
                "input": "hello",
                "response_format": "wav",
            },
        )
    assert response.status_code == 502
