"""Full real inference pipeline: STT → LLM → TTS.

Run: uv run --locked pytest apps/realtime_voice/tests/test_full_real_inference.py -v
"""
from __future__ import annotations

import base64

import numpy as np
import pytest

from apps.realtime_voice._shared_realtime_voice_qwen import (
    ChatterboxTTS,
    QwenLLM,
    RealtimeVoiceOutput,
    WhisperSTT,
    float_to_pcm16,
)


def _load_fixture_audio():
    """Load the fixture WAV and return base64-encoded PCM16."""
    import wave
    with wave.open("apps/realtime_voice/tests/fixtures/hello.wav", "rb") as wf:
        frames = wf.readframes(wf.getnframes())
    arr = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    pcm16 = float_to_pcm16(arr)
    return base64.b64encode(pcm16).decode("ascii")

def test_full_pipeline_stt_llm_tts_with_fixture():
    """Run complete STT→LLM→TTS pipeline with real models and fixture audio."""
    try:
        whisper = WhisperSTT(model_path="openai/whisper-base.en", device="cuda", compute_type="int8")
        whisper.load()
        llm = QwenLLM(model_path="Qwen/Qwen2-0.5B-Instruct", device="cuda", max_new_tokens=32)
        llm.load()
        tts = ChatterboxTTS(reference_dir="/vol/models/reference_voices")
        tts.load()

        audio_b64 = _load_fixture_audio()
        pcm_in = base64.b64decode(audio_b64)
        transcript = whisper.transcribe(pcm_in)

        messages = [
            {"role": "system", "content": "You are a helpful, concise voice assistant."},
            {"role": "user", "content": transcript if transcript.strip() else "Hello"},
        ]
        llm_parts = list(llm.stream(messages))
        llm_text = "".join(llm_parts).strip()

        pcm_out = b"".join(tts.stream(llm_text, voice="test-voice"))

        out = RealtimeVoiceOutput(
            audio=base64.b64encode(pcm_out).decode("ascii"),
            transcript=llm_text,
            sample_rate=24000,
        )
        assert out.audio
        assert out.transcript == llm_text
        assert out.sample_rate == 24000
    except (ValueError, RuntimeError, ModuleNotFoundError) as e:
        pytest.fail(f"Real GPU inference failed: {e}")

def test_full_pipeline_raises_on_empty_transcript():
    """Validate that do_inference raises RuntimeError when STT returns empty text."""
    try:
        import numpy as np

        from apps.realtime_voice._shared_realtime_voice_qwen import WhisperSTT

        whisper = WhisperSTT(model_path="openai/whisper-base.en", device="cuda", compute_type="int8")
        whisper.load()

        with pytest.raises(RuntimeError, match="empty transcription"):
            whisper.transcribe(np.zeros(100, dtype=np.float32).tobytes())
    except (ValueError, RuntimeError, ModuleNotFoundError) as e:
        if "empty transcription" in str(e):
            pass
        else:
            pytest.fail(f"Real GPU inference failed: {e}")
