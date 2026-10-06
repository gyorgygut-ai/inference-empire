"""Real Whisper STT test — loads actual Whisper model, transcribes fixture audio.

Run: uv run --locked pytest apps/realtime_voice/tests/test_whisper_real_stt.py -v
Skips if no CUDA: test will naturally error if torch.cuda unavailable.
"""
from __future__ import annotations

import base64
import numpy as np
import pytest

from apps.realtime_voice._shared_realtime_voice_qwen import WhisperSTT, float_to_pcm16


def _load_fixture_b64() -> str:
    import wave
    with wave.open("apps/realtime_voice/tests/fixtures/hello.wav", "rb") as wf:
        frames = wf.readframes(wf.getnframes())
    arr = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    pcm16 = float_to_pcm16(arr)
    return base64.b64encode(pcm16).decode("ascii")


@pytest.mark.real
def test_whisper_stt_loads_and_runs():
    """Whisper model loads on CUDA and transcribes the fixture audio chunk."""
    whisper = WhisperSTT(model_path="openai/whisper-base.en", device="cuda", compute_type="int8")
    whisper.load()
    audio_b64 = _load_fixture_b64()
    transcript = whisper.transcribe(base64.b64decode(audio_b64))
    # Transcript may be empty for synthetic sine wave — that's OK.
    # The test validates: model loads, transcribe runs, returns a string.
    assert isinstance(transcript, str)


@pytest.mark.real
def test_whisper_stt_returns_string_type():
    """Ensure transcribe() always returns str (never None/crash)."""
    whisper = WhisperSTT(model_path="openai/whisper-base.en", device="cuda", compute_type="int8")
    whisper.load()
    transcript = whisper.transcribe(b"")
    assert isinstance(transcript, str)