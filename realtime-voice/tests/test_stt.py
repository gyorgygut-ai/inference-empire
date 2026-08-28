"""STT handler test — skipped unless model tests are explicitly enabled.

Heavy (downloads/loads Whisper + needs a GPU). Run in the Beam container with
``BEAM_VOICE_TEST_MODELS=1`` and ``WHISPER_MODEL_PATH`` pointing at the
seeded volume path.
"""

from __future__ import annotations

import os

import pytest

numpy = pytest.importorskip("numpy")
pytest.importorskip("faster_whisper")

from handlers.stt import WhisperSTT  # noqa: E402
from realtime.audio import float_to_pcm16  # noqa: E402


@pytest.mark.skipif(
    os.environ.get("BEAM_VOICE_TEST_MODELS") != "1",
    reason="set BEAM_VOICE_TEST_MODELS=1 and WHISPER_MODEL_PATH to run",
)
def test_transcribe_synthetic_silence():
    path = os.environ["WHISPER_MODEL_PATH"]
    stt = WhisperSTT(path).load()
    # 1 second of (near) silence @ 24 kHz -> should transcribe to empty string.
    pcm24 = float_to_pcm16(np.zeros(24000, dtype=np.float32))
    text = stt.transcribe(pcm24)
    assert isinstance(text, str)
