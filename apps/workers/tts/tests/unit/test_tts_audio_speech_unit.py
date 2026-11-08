import base64
import io
import os
import wave

import numpy as np
import pytest
from dist.contract_tts_audio_speech import Input, Output
from fastapi.testclient import TestClient
from shared.worker_tts_audio_speech import (
    build_app,
    encode_audio,
    stream_synthesize,
    synthesize,
)
from tests.stub_services import tts_generator_stub

TTS_API_KEY = "tts-test-key"


@pytest.fixture
def client():
    os.environ["TTS_AUDIO_SPEECH_API_KEY"] = TTS_API_KEY
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


def test_tts_null_voice_uses_alloy_default(client):
    response = client.post(
        "/v1/audio/speech",
        headers={"Authorization": f"Bearer {TTS_API_KEY}"},
        json={
            "model": "resembleai_chatterbox_tts",
            "input": "hello world",
            "voice": None,
            "response_format": "wav",
        },
    )
    assert response.status_code == 200


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


def test_tts_stream_endpoint_yields_pcm_chunks_and_sample_rate():
    chunks = [np.array([100, -100], dtype=np.int16), np.array([200], dtype=np.int16)]

    def streaming_generator(_request):
        yield from (chunk.tobytes() for chunk in chunks)

    app = build_app(
        generator=tts_generator_stub,
        streaming_generator=streaming_generator,
        api_key=TTS_API_KEY,
    )
    with TestClient(app) as client:
        response = client.post(
            "/v1/audio/speech/stream",
            headers={"Authorization": f"Bearer {TTS_API_KEY}"},
            json={
                "model": "resembleai_chatterbox_tts",
                "input": "hello world",
                "response_format": "wav",
            },
        )

    assert response.status_code == 200
    assert response.headers["x-sample-rate"] == "24000"
    np.testing.assert_array_equal(
        np.frombuffer(response.content, dtype=np.int16),
        np.concatenate(chunks),
    )


def test_stream_synthesize_yields_each_model_chunk_as_pcm16():
    class AudioChunk:
        def __init__(self, samples):
            self.samples = samples

        def squeeze(self):
            return self

        def detach(self):
            return self

        def cpu(self):
            return self

        def __array__(self, dtype=None):
            return np.asarray(self.samples, dtype=dtype)

    class StreamingModel:
        sr = 24_000

        def generate_stream(self, text, **kwargs):
            assert text == "hello streaming"
            assert kwargs == {}
            yield AudioChunk(np.array([[0.25, -0.25]], dtype=np.float32)), None
            yield AudioChunk(np.array([[0.5]], dtype=np.float32)), None

    chunks = list(
        stream_synthesize(
            Input(model="resembleai_chatterbox_tts", input="hello streaming"),
            model=StreamingModel(),
        )
    )

    assert len(chunks) == 2
    np.testing.assert_array_equal(
        np.frombuffer(chunks[0], dtype=np.int16), np.array([8191, -8191], dtype=np.int16)
    )
    np.testing.assert_array_equal(
        np.frombuffer(chunks[1], dtype=np.int16), np.array([16383], dtype=np.int16)
    )


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


def test_synthesize_uses_reference_audio_prompt():
    class FakeGenerated:
        def squeeze(self):
            return self

        def detach(self):
            return self

        def cpu(self):
            return self

        def __array__(self, dtype=None):
            return np.asarray(np.ones(240, dtype=np.float32) * 0.1, dtype=dtype)

    class FakeModel:
        sr = 24_000

        def generate(self, text, **kwargs):
            assert text == "hello from a reference voice"
            reference_path = kwargs["audio_prompt_path"]
            with wave.open(reference_path, "rb") as reference:
                assert reference.getnchannels() == 1
                assert reference.getframerate() == 24_000
                assert reference.readframes(reference.getnframes())
            return FakeGenerated()

    reference_audio = base64.b64decode(
        encode_audio(np.ones(240, dtype=np.float32) * 0.1, 24_000).audio_base64,
        validate=True,
    )
    reference = base64.b64encode(reference_audio).decode("ascii")
    request = Input(
        model="resembleai_chatterbox_tts",
        input="hello from a reference voice",
        voice="GUT",
        reference_audio_base64=reference,
    )

    response = synthesize(request, model=FakeModel())
    assert response.format == "wav"
    assert response.sample_rate == 24_000


def test_synthesize_null_voice_uses_alloy_without_reference():
    class FakeGenerated:
        def squeeze(self):
            return self

        def detach(self):
            return self

        def cpu(self):
            return self

        def __array__(self, dtype=None):
            return np.asarray(np.ones(240, dtype=np.float32) * 0.1, dtype=dtype)

    class FakeModel:
        sr = 24_000

        def generate(self, text, **kwargs):
            assert text == "alloy output"
            assert kwargs == {}
            return FakeGenerated()

    response = synthesize(
        Input(
            model="resembleai_chatterbox_tts",
            input="alloy output",
            voice=None,
        ),
        model=FakeModel(),
    )
    assert response.format == "wav"
    assert response.sample_rate == 24_000
