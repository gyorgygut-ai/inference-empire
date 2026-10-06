"""Real WebRTC handler test — handle_webrtc_audio with real models.

Run: uv run --locked pytest apps/realtime_voice/tests/test_webrtc_real_audio.py -v
Skips if no CUDA — test will naturally error if torch.cuda is unavailable.
"""
from __future__ import annotations

import numpy as np
import pytest

from apps.realtime_voice._shared_realtime_voice_qwen import handle_webrtc_audio


@pytest.mark.real
def test_webrtc_handler_real_audio_roundtrip():
    """handle_webrtc_audio with real models returns (24000, non-empty ndarray)."""
    # Load real models
    from apps.realtime_voice._shared_realtime_voice_qwen import (
        WhisperSTT,
        QwenLLM,
        ChatterboxTTS,
    )
    whisper = WhisperSTT(model_path="openai/whisper-base.en", device="cuda", compute_type="int8")
    whisper.load()
    llm = QwenLLM(model_path="Qwen/Qwen2-0.5B-Instruct", device="cuda", max_new_tokens=32)
    llm.load()
    tts = ChatterboxTTS(reference_dir="/vol/models/reference_voices")
    tts.load()

    models = {"stt": whisper, "llm": llm, "tts": tts}

    # Generate a small float32 array (1 second at 24kHz)
    audio_chunk = np.zeros(2400, dtype=np.float32)

    sr, arr = handle_webrtc_audio(models, 24000, audio_chunk)
    assert sr == 24000
    assert len(arr) > 0
    assert arr.dtype == np.float32