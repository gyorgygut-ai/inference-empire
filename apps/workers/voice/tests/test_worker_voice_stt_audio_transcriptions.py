from __future__ import annotations

import base64
from types import SimpleNamespace

import pytest
from dist.contract_voice_stt_audio_transcriptions import Input
from fastapi.testclient import TestClient
from shared.worker_voice_stt_audio_transcriptions import (
    build_app,
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


def test_transcription_route_requires_generated_api_key(monkeypatch) -> None:
    monkeypatch.setenv("GENERATED_STT_AUDIO_TRANSCRIPTIONS_API_KEY", "stt-test-key")
    app = build_app(transcriber=lambda _: transcription_output("recognized words"))
    client = TestClient(app)
    payload = {"model": "whisper-1"}
    audio = {"file": ("audio.wav", b"audio fixture", "audio/wav")}

    accepted = client.post(
        "/v1/audio/transcriptions",
        headers={"Authorization": "Bearer stt-test-key"},
        data=payload,
        files=audio,
    )
    rejected = client.post(
        "/v1/audio/transcriptions",
        headers={"Authorization": "Bearer wrong-key"},
        data=payload,
        files=audio,
    )

    assert accepted.status_code == 200 and accepted.json()["text"] == "recognized words"
    assert rejected.status_code == 401
