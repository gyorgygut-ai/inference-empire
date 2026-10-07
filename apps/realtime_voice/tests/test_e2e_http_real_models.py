"""Real HTTP endpoint test — POST /v1/voice:turn with real models and fixture audio.

Run: uv run --locked pytest apps/realtime_voice/tests/test_http_real_models.py -v
"""
from __future__ import annotations

import base64

import numpy as np
import pytest
from fastapi.testclient import TestClient

from apps.realtime_voice._shared_realtime_voice_qwen import (
    RealtimeVoiceOutput,
    build_app,
)


def _load_fixture_audio_b64():
    import wave
    with wave.open("apps/realtime_voice/tests/fixtures/hello.wav", "rb") as wf:
        frames = wf.readframes(wf.getnframes())
    arr = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    from apps.realtime_voice._shared_realtime_voice_qwen import float_to_pcm16
    pcm16 = float_to_pcm16(arr)
    return base64.b64encode(pcm16).decode("ascii")

def test_http_voice_turn_endpoint_returns_contract():
    """POST /v1/voice:turn with real models returns 200 + valid contract output."""
    try:
        from apps.realtime_voice._shared_realtime_voice_qwen import (
            ChatterboxTTS,
            QwenLLM,
            WhisperSTT,
        )
        whisper = WhisperSTT(model_path="openai/whisper-base.en", device="cuda", compute_type="int8")
        whisper.load()
        llm = QwenLLM(model_path="Qwen/Qwen2-0.5B-Instruct", device="cuda", max_new_tokens=32)
        llm.load()
        tts = ChatterboxTTS(reference_dir="/vol/models/reference_voices")
        tts.load()

        models = {"stt": whisper, "llm": llm, "tts": tts}
        app = build_app(models)

        with TestClient(app) as client:
            audio_b64 = _load_fixture_audio_b64()
            res = client.post(
                "/v1/voice:turn",
                json={"audio": audio_b64, "voice": "test-voice"},
            )
            assert res.status_code == 200
            out = res.json()
            assert out["transcript"], "transcript should not be empty"
            assert base64.b64decode(out["audio"]), "audio should be non-empty"
            assert out["sample_rate"] == 24000
            validated = RealtimeVoiceOutput(**out)
            assert validated.model_dump() == out
    except (ValueError, RuntimeError, ModuleNotFoundError) as e:
        pytest.fail(f"Real GPU inference failed: {e}")
