from __future__ import annotations

from dist.contract_voice_stt_audio_transcriptions import Input, Output
from fastapi.testclient import TestClient
from shared.worker_voice_stt_audio_transcriptions import build_app


def test_audio_transcriptions_multipart_request_returns_json_transcript() -> None:
    requests: list[Input] = []

    def transcribe(request: Input) -> Output:
        requests.append(request)
        return Output(text="deterministic local transcript")

    client = TestClient(build_app(transcribe))
    response = client.post(
        "/v1/audio/transcriptions",
        files={"file": ("sample.wav", b"local audio fixture", "audio/wav")},
        data={"model": "whisper-1", "language": "en", "temperature": "0"},
    )

    assert response.status_code == 200
    assert response.json() == {"text": "deterministic local transcript"}
    assert requests[0].model == "whisper-1"
    assert requests[0].filename == "sample.wav"
