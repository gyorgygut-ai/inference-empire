import io
import os
import wave

import pytest
from fastapi.testclient import TestClient
from shared.worker_stt_audio_transcriptions import build_app
from tests.stub_services import stt_transcriber_stub

STT_API_KEY = "stt-test-key"


def wav_fixture(
    *, sample_rate: int = 24_000, channels: int = 1, amplitude: int = 1000
) -> bytes:
    samples = [amplitude] * 240
    if channels == 2:
        samples = [sample for value in samples for sample in (value, value)]
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"".join(sample.to_bytes(2, "little", signed=True) for sample in samples))
    return buffer.getvalue()


@pytest.fixture
def client():
    os.environ["SECRET_STT_AUDIO_TRANSCRIPTIONS_API_KEY"] = STT_API_KEY
    app = build_app(transcriber=stt_transcriber_stub)
    return TestClient(app)


def test_stt_health_returns_200(client):
    r = client.get("/health")
    assert r.status_code == 200, "health check failed"


def test_stt_health_response_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_stt_missing_or_invalid_token_returns_401(client):
    # Missing auth header
    r = client.post(
        "/v1/audio/transcriptions",
        files={"file": ("audio.wav", b"", "audio/wav")},
        data={"model": "faster_whisper_large_v3"},
    )
    assert r.status_code == 401, "missing token not rejected"

    # Invalid token
    r = client.post(
        "/v1/audio/transcriptions",
        headers={"Authorization": "Bearer bad"},
        files={"file": ("audio.wav", b"", "audio/wav")},
        data={"model": "faster_whisper_large_v3"},
    )
    assert r.status_code == 401, "invalid token not rejected"


def test_stt_missing_or_invalid_token_response_error(client):
    r = client.post(
        "/v1/audio/transcriptions",
        headers={"Authorization": "Bearer bad"},
        files={"file": ("audio.wav", b"", "audio/wav")},
        data={"model": "faster_whisper_large_v3"},
    )
    assert r.status_code == 401
    assert "detail" in r.json(), "missing detail in error response"


@pytest.mark.parametrize(
    "audio",
    [
        b"",
        b"not audio",
        wav_fixture(sample_rate=16_000),
        wav_fixture(channels=2),
        wav_fixture(amplitude=0),
        wav_fixture(amplitude=10),
    ],
    ids=["empty", "malformed", "wrong-rate", "stereo", "silent", "near-silent"],
)
def test_stt_invalid_audio_returns_422(client, audio):
    response = client.post(
        "/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {STT_API_KEY}"},
        files={"file": ("audio.wav", audio, "audio/wav")},
        data={"model": "faster_whisper_large_v3"},
    )
    assert response.status_code == 422
    assert "detail" in response.json()


def test_stt_valid_fixture_returns_200(client):
    audio = wav_fixture()
    r = client.post(
        "/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {STT_API_KEY}"},
        files={"file": ("audio.wav", audio, "audio/wav")},
        data={"model": "faster_whisper_large_v3"},
    )
    assert r.status_code == 200, "valid audio request failed"


def test_stt_valid_fixture_response_text_non_empty(client):
    audio = wav_fixture()
    r = client.post(
        "/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {STT_API_KEY}"},
        files={"file": ("audio.wav", audio, "audio/wav")},
        data={"model": "faster_whisper_large_v3"},
    )
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("text"), str) and data["text"].strip(), "empty transcript"
