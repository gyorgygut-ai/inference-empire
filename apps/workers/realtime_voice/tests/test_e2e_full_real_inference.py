"""Full real inference pipeline: STT → LLM → TTS.

Run: uv run --locked pytest apps/realtime_voice/tests/test_e2e_full_real_inference.py -v
"""
from __future__ import annotations

import base64
import os

import numpy as np
import shared.worker_realtime_voice as shared
from shared.worker_realtime_voice import float_to_pcm16


def _load_fixture_audio():
    """Load the fixture WAV and return base64-encoded PCM16."""
    import wave

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "hello.wav")
    with wave.open(path, "rb") as wf:
        frames = wf.readframes(wf.getnframes())
    arr = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    pcm16 = float_to_pcm16(arr)
    return base64.b64encode(pcm16).decode("ascii")


def test_full_pipeline_stt_llm_tts_with_fixture():
    """Run complete STT→LLM→TTS pipeline with real models and fixture audio."""
    models = shared.load_dependencies()
    req = shared.RealtimeVoiceInput(audio=_load_fixture_audio(), voice="gyorgy")
    out = shared.do_inference(models, req)
    assert out.transcript.strip()
    pcm = base64.b64decode(out.audio)
    assert len(pcm) > 0 and any(pcm)
    assert out.sample_rate == 24000
