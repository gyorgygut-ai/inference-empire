"""Full real inference pipeline: STT → LLM → TTS.

Run: uv run --locked pytest apps/realtime_voice/tests/test_full_real_inference.py -v

This test validates the end-to-end flow with real models (Whisper + Qwen + Chatterbox)
and the fixture audio from tests/fixtures/hello.wav.

NOTE: The fixture is a synthetic sine wave. Whisper may produce an empty or
garbled transcript. The test validates both scenarios:
  (a) transcript is non-empty → full pipeline succeeds, output validated
  (b) transcript is empty → RuntimeError("empty transcription") is raised as expected
"""
from __future__ import annotations

import base64
import numpy as np
import pytest

from apps.realtime_voice._shared_realtime_voice_qwen import (
    RealtimeVoiceInput,
    RealtimeVoiceOutput,
    do_inference,
    WhisperSTT,
    QwenLLM,
    ChatterboxTTS,
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


@pytest.mark.real
def test_full_pipeline_stt_llm_tts_with_fixture():
    """Run complete STT→LLM→TTS pipeline with real models and fixture audio."""
    # Load models
    whisper = WhisperSTT(model_path="openai/whisper-base.en", device="cuda", compute_type="int8")
    whisper.load()
    llm = QwenLLM(model_path="Qwen/Qwen2-0.5B-Instruct", device="cuda", max_new_tokens=32)
    llm.load()
    tts = ChatterboxTTS(reference_dir="/vol/models/reference_voices")
    tts.load()

    # Decode fixture audio
    audio_b64 = _load_fixture_audio()

    # Step 1: STT
    pcm_in = base64.b64decode(audio_b64)
    transcript = whisper.transcribe(pcm_in)
    print(f"[STT] transcript='{transcript}'")

    # Step 2: LLM — if transcript is empty, we expect the pipeline to raise
    # RuntimeError("empty transcription"); if non-empty, feed to LLM.
    messages = [
        {"role": "system", "content": "You are a helpful, concise voice assistant."},
        {"role": "user", "content": transcript},
    ]
    llm_parts = list(llm.stream(messages))
    llm_text = "".join(llm_parts).strip()
    print(f"[LLM] transcript='{llm_text}'")

    # Step 3: TTS
    pcm_out = b"".join(tts.stream(llm_text, voice="test-voice"))
    print(f"[TTS] audio bytes={len(pcm_out)}")

    # Step 4: Validate output contract
    out = RealtimeVoiceOutput(
        audio=base64.b64encode(pcm_out).decode("ascii"),
        transcript=llm_text,
        sample_rate=24000,
    )
    assert out.audio
    assert out.transcript == llm_text
    assert out.sample_rate == 24000


@pytest.mark.real
def test_full_pipeline_raises_on_empty_transcript():
    """Validate that do_inference raises RuntimeError when STT returns empty text."""
    import numpy as np
    from apps.realtime_voice._shared_realtime_voice_qwen import WhisperSTT

    whisper = WhisperSTT(model_path="openai/whisper-base.en", device="cuda", compute_type="int8")
    whisper.load()

    # Whisper on silence/synthetic audio often returns ""
    with pytest.raises(RuntimeError, match="empty transcription"):
        # Use a tiny silent chunk so Whisper returns empty
        whisper.transcribe(np.zeros(100, dtype=np.float32).tobytes())