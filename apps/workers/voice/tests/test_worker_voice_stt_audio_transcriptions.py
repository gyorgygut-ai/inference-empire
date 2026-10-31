from __future__ import annotations

import base64
from types import SimpleNamespace

import pytest
from dist.contract_voice_stt_audio_transcriptions import Input
from shared.worker_voice_stt_audio_transcriptions import (
    decode_audio,
    transcribe,
    transcription_output,
)


def test_transcription_decodes_audio_and_returns_non_empty_text() -> None:
    audio = b"deterministic audio fixture"
    request = Input(
        model="whisper-1",
        file_base64=base64.b64encode(audio).decode("ascii"),
        language="en",
        temperature=0,
    )

    class Engine:
        def transcribe(self, path, **options):
            with open(path, "rb") as audio_file:
                assert audio_file.read() == audio
            assert options == {
                "language": "en",
                "initial_prompt": None,
                "temperature": 0.0,
            }
            return iter([SimpleNamespace(text=" recognized words ")]), None

    assert decode_audio(request) == audio
    assert transcribe(request, Engine()).text == "recognized words"


@pytest.mark.parametrize(
    ("encoded", "message"),
    [("%%%", "Audio file must be valid base64"), ("", "Audio file is empty")],
)
def test_invalid_audio_is_rejected(encoded: str, message: str) -> None:
    request = Input(model="whisper-1", file_base64=encoded)

    with pytest.raises(ValueError, match=message):
        decode_audio(request)


def test_empty_transcript_is_rejected() -> None:
    with pytest.raises(ValueError, match="empty transcript"):
        transcription_output("  ")
