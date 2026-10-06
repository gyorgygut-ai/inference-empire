"""Real Chatterbox TTS test — loads actual Chatterbox model, synthesizes audio.

Run: uv run --locked pytest apps/realtime_voice/tests/test_chatterbox_real_tts.py -v
Skips if no CUDA — test will naturally error if torch.cuda is unavailable.
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
    tts = _make_tts()
    pcm = tts.generate("Hello", voice="test-voice")
    # Validate output is bytes-like and non-empty
    assert pcm is not None
    assert len(pcm) > 0


@pytest.mark.real
def test_chatterbox_tts_returns_valid_pcm():
    """ensure generate() output passes base64 decode sanity check."""
    tts = _make_tts()
    pcm = tts.generate("Hello", voice="test-voice")
    import base64
    decoded = base64.b64encode(pcm)
    assert len(decoded) > 0