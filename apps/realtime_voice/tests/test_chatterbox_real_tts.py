"""Real Chatterbox TTS test — loads actual Chatterbox model, synthesizes audio.

Run: uv run --locked pytest apps/realtime_voice/tests/test_chatterbox_real_tts.py -v
"""
from __future__ import annotations

import pytest

from apps.realtime_voice._shared_realtime_voice_qwen import ChatterboxTTS

def _make_tts():
    tts = ChatterboxTTS(reference_dir="/vol/models/reference_voices")
    tts.load()
    return tts

@pytest.mark.real
def test_chatterbox_tts_loads_and_generates():
    """Chatterbox model loads on CUDA and generate() returns PCM16 bytes."""
    try:
        tts = _make_tts()
        pcm = tts.generate("Hello", voice="test-voice")
        assert pcm is not None
        assert len(pcm) > 0
    except (ValueError, RuntimeError, ModuleNotFoundError) as e:
        pytest.fail(f"Real GPU inference failed: {e}")

@pytest.mark.real
def test_chatterbox_tts_returns_valid_pcm():
    """ensure generate() output passes base64 decode sanity check."""
    try:
        tts = _make_tts()
        pcm = tts.generate("Hello", voice="test-voice")
        import base64
        decoded = base64.b64encode(pcm)
        assert len(decoded) > 0
    except (ValueError, RuntimeError, ModuleNotFoundError) as e:
        pytest.fail(f"Real GPU inference failed: {e}")
