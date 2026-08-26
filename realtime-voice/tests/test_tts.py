"""TTS handler test — skipped unless model tests are explicitly enabled.

Heavy (loads Qwen3-TTS 1.7B + needs a GPU). Run in the Beam container with
``BEAM_VOICE_TEST_MODELS=1`` and ``TTS_MODEL_PATH`` pointing at the seeded
volume path.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("faster_qwen3_tts")

from handlers.tts import QwenTTS  # noqa: E402


@pytest.mark.skipif(
    os.environ.get("BEAM_VOICE_TEST_MODELS") != "1",
    reason="set BEAM_VOICE_TEST_MODELS=1 and TTS_MODEL_PATH to run",
)
def test_stream_yields_pcm():
    path = os.environ["TTS_MODEL_PATH"]
    tts = QwenTTS(path).load()
    chunks = list(tts.stream("Hello there."))
    assert chunks, "expected at least one PCM chunk"
    assert all(isinstance(c, bytes) and len(c) % 2 == 0 for c in chunks)
