from __future__ import annotations

import base64
import io

import numpy as np
import pytest
import soundfile as sf
from dist.contract_voice_tts_audio_speech import Input, Output
from fastapi.testclient import TestClient
from shared.worker_voice_tts_audio_speech import (
    MODELS,
    build_app,
    encode_audio,
    synthesize,
)


class FakeTensor:
    def squeeze(self) -> FakeTensor:
        return self

    def detach(self) -> FakeTensor:
        return self

    def cpu(self) -> np.ndarray:
        return np.sin(np.linspace(0, 20, 2400, dtype=np.float32)) * 0.2


class FakeChatterbox:
    sr = 24_000

    def generate(self, text: str) -> FakeTensor:
        assert text == "Hello there."
        return FakeTensor()


def test_contract_rejects_empty_text_and_unsupported_audio_format():
    with pytest.raises(ValueError):
        Input.model_validate({"model": "chatterbox", "input": ""})
    with pytest.raises(ValueError):
        Input.model_validate({"model": "chatterbox", "input": "Hello", "response_format": "mp3"})


def test_model_mapping_declares_chatterbox_model_and_cache():
    assert MODELS == {
        "resembleai_chatterbox_tts": {
            "url": "https://huggingface.co/ResembleAI/chatterbox",
            "path": "./hf-cache/resembleai_chatterbox_tts",
        }
    }


def test_synthesis_encodes_valid_non_silent_wav_without_loading_model():
    output = synthesize(
        Input(model="chatterbox", input="Hello there."),
        model=FakeChatterbox(),
    )

    audio = base64.b64decode(output.audio_base64)
    samples, sample_rate = sf.read(io.BytesIO(audio), dtype="float32")
    assert output.format == "wav"
    assert sample_rate == 24_000
    assert samples.size > 0
    assert float(np.max(np.abs(samples))) >= 0.001


def test_audio_encoder_rejects_silent_output():
    with pytest.raises(ValueError, match="silent"):
        encode_audio(np.zeros(100, dtype=np.float32), 24_000)


def test_speech_route_returns_audio_and_rejects_silent_response(monkeypatch):
    monkeypatch.setenv("GENERATED_TTS_AUDIO_SPEECH_API_KEY", "tts-test-key")
    audio = encode_audio(np.sin(np.linspace(0, 20, 2400)) * 0.2, 24_000)
    client = TestClient(build_app(generator=lambda _: audio))
    response = client.post(
        "/v1/audio/speech",
        headers={"Authorization": "Bearer tts-test-key"},
        json={"model": "chatterbox", "input": "Hello there."},
    )
    silent_buffer = io.BytesIO()
    sf.write(silent_buffer, np.zeros(100, dtype=np.float32), 24_000, format="WAV")
    silent_output = Output(
        audio_base64=base64.b64encode(silent_buffer.getvalue()).decode("ascii"),
        format="wav",
        sample_rate=24_000,
    )
    silent_client = TestClient(build_app(generator=lambda _: silent_output))
    silent = silent_client.post(
        "/v1/audio/speech",
        headers={"Authorization": "Bearer tts-test-key"},
        json={"model": "chatterbox", "input": "Hello there."},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert len(response.content) > 44
    assert silent.status_code == 502


def test_speech_route_rejects_invalid_generated_api_key(monkeypatch):
    monkeypatch.setenv("GENERATED_TTS_AUDIO_SPEECH_API_KEY", "tts-test-key")
    client = TestClient(
        build_app(generator=lambda _: pytest.fail("unauthorized request reached model"))
    )
    response = client.post(
        "/v1/audio/speech",
        headers={"Authorization": "Bearer wrong-key"},
        json={"model": "chatterbox", "input": "Hello there."},
    )

    assert response.status_code == 401
