import base64
import io
import os
import wave
from dataclasses import dataclass
from pathlib import Path

import httpx
import numpy as np
import pytest
from shared.inference_client import InferenceClient, InferenceEndpoint
from shared.worker_voice import SYSTEM_MESSAGE, run_turn

FIXTURE = Path(__file__).parents[1] / "fixtures" / "message.wav"
SAMPLE_RATE = 24_000


@dataclass(frozen=True)
class Service:
    url: str
    token: str
    path: str


@dataclass(frozen=True)
class Backend:
    stt: Service
    llm: Service
    tts: Service
    is_stub: bool


BACKENDS = {
    "stub": Backend(
        stt=Service(
            os.environ["STUB_STT_AUDIO_TRANSCRIPTIONS_API_URL"].rstrip("/"),
            os.environ["STUB_STT_AUDIO_TRANSCRIPTIONS_API_KEY"],
            "/v1/audio/transcriptions",
        ),
        llm=Service(
            os.environ["STUB_LLM_CHAT_COMPLETIONS_API_URL"].rstrip("/"),
            os.environ["STUB_LLM_CHAT_COMPLETIONS_API_KEY"],
            "/v1/chat/completions",
        ),
        tts=Service(
            os.environ["STUB_TTS_AUDIO_SPEECH_API_URL"].rstrip("/"),
            os.environ["STUB_TTS_AUDIO_SPEECH_API_KEY"],
            "/v1/audio/speech",
        ),
        is_stub=True,
    ),
    "real": Backend(
        stt=Service(
            os.environ["REAL_STT_AUDIO_TRANSCRIPTIONS_API_URL"].rstrip("/"),
            os.environ["REAL_STT_AUDIO_TRANSCRIPTIONS_API_KEY"],
            "/v1/audio/transcriptions",
        ),
        llm=Service(
            os.environ["REAL_LLM_CHAT_COMPLETIONS_API_URL"].rstrip("/"),
            os.environ["REAL_LLM_CHAT_COMPLETIONS_API_KEY"],
            "/v1/chat/completions",
        ),
        tts=Service(
            os.environ["REAL_TTS_AUDIO_SPEECH_API_URL"].rstrip("/"),
            os.environ["REAL_TTS_AUDIO_SPEECH_API_KEY"],
            "/v1/audio/speech",
        ),
        is_stub=False,
    ),
}


@pytest.fixture(params=tuple(BACKENDS), ids=tuple(BACKENDS))
def backend(request) -> Backend:
    return BACKENDS[request.param]


@pytest.mark.parametrize("service_name", ["stt", "llm", "tts"])
def test_dependency_health_is_ok(backend: Backend, service_name: str) -> None:
    service = getattr(backend, service_name)
    response = httpx.get(f"{service.url}/health", timeout=10)

    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("service_name", ["stt", "llm", "tts"])
def test_dependency_rejects_invalid_bearer_token(
    backend: Backend, service_name: str
) -> None:
    service = getattr(backend, service_name)
    if service_name == "stt":
        response = httpx.post(
            f"{service.url}{service.path}",
            headers={"Authorization": "Bearer invalid"},
            data={"model": "configured", "response_format": "json"},
            files={"file": ("test.wav", b"RIFF", "audio/wav")},
            timeout=15,
        )
    elif service_name == "llm":
        response = httpx.post(
            f"{service.url}{service.path}",
            headers={"Authorization": "Bearer invalid"},
            json={
                "model": "configured",
                "messages": [{"role": "user", "content": "test"}],
            },
            timeout=15,
        )
    else:
        response = httpx.post(
            f"{service.url}{service.path}",
            headers={"Authorization": "Bearer invalid"},
            json={
                "model": "configured",
                "input": "test",
                "response_format": "wav",
            },
            timeout=15,
        )

    assert response.status_code == 401, response.text


def test_stt_transcribes_fixture_audio(backend: Backend) -> None:
    with wave.open(str(FIXTURE), "rb") as audio:
        assert (audio.getframerate(), audio.getnchannels(), audio.getsampwidth()) == (
            SAMPLE_RATE,
            1,
            2,
        )

    response = httpx.post(
        f"{backend.stt.url}{backend.stt.path}",
        headers={"Authorization": f"Bearer {backend.stt.token}"},
        data={"model": "configured", "response_format": "json"},
        files={"file": (FIXTURE.name, FIXTURE.read_bytes(), "audio/wav")},
        timeout=120,
    )

    assert response.status_code == 200, response.text
    assert response.json()["text"].strip()
    assert "presigned_url" not in response.json()


def test_llm_returns_completion_for_transcript(backend: Backend) -> None:
    response = httpx.post(
        f"{backend.llm.url}{backend.llm.path}",
        headers={"Authorization": f"Bearer {backend.llm.token}"},
        json={
            "model": "configured",
            "messages": [{"role": "user", "content": "Fixture transcript"}],
        },
        timeout=120,
    )

    assert response.status_code == 200, response.text
    assert response.json()["choices"][0]["message"]["content"].strip()


def test_tts_returns_non_silent_24khz_wav(backend: Backend) -> None:
    response = httpx.post(
        f"{backend.tts.url}{backend.tts.path}",
        headers={"Authorization": f"Bearer {backend.tts.token}"},
        json={
            "model": "configured",
            "input": "Fixture reply",
            "voice": "alloy",
            "response_format": "wav",
        },
        timeout=120,
    )

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["format"] == "wav"
    assert result["sample_rate"] == SAMPLE_RATE

    wav_bytes = base64.b64decode(result["audio_base64"], validate=True)
    with wave.open(io.BytesIO(wav_bytes), "rb") as audio:
        assert (audio.getframerate(), audio.getnchannels(), audio.getsampwidth()) == (
            SAMPLE_RATE,
            1,
            2,
        )
        samples = np.frombuffer(
            audio.readframes(audio.getnframes()), dtype="<i2"
        ).astype(np.float64)

    assert samples.size > 0
    assert float(np.sqrt(np.mean(np.square(samples)))) > 32


def _stub_request_counts(backend: Backend) -> dict[str, int]:
    counts = {}
    for name in ("stt", "llm", "tts"):
        service = getattr(backend, name)
        response = httpx.get(f"{service.url}/__test__/metrics", timeout=10)
        assert response.status_code == 200, response.text
        counts[name] = response.json()["requests"]
    return counts


def _reset_stub_request_counts(backend: Backend) -> None:
    for name in ("stt", "llm", "tts"):
        service = getattr(backend, name)
        response = httpx.post(f"{service.url}/__test__/reset", timeout=10)
        assert response.status_code == 200, response.text


def test_voice_pipeline_runs_stt_llm_tts_for_backend(backend: Backend) -> None:
    client = InferenceClient(
        stt=InferenceEndpoint(backend.stt.url, backend.stt.token),
        llm=InferenceEndpoint(backend.llm.url, backend.llm.token),
        tts=InferenceEndpoint(backend.tts.url, backend.tts.token),
    )

    before = {}
    if backend.is_stub:
        _reset_stub_request_counts(backend)
        before = _stub_request_counts(backend)

    with wave.open(str(FIXTURE), "rb") as audio:
        samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2")
        sample_rate = audio.getframerate()

    transcript, reply = run_turn(
        samples,
        sample_rate,
        client,
        [{"role": "system", "content": SYSTEM_MESSAGE}],
    )
    chunks = list(client.stream_speak(reply, "alloy"))
    output = np.concatenate(chunks) if chunks else np.array([], dtype=np.int16)

    assert transcript.strip()
    assert reply.strip()
    assert output.dtype == np.int16
    assert output.size > 0
    assert float(np.sqrt(np.mean(np.square(output.astype(np.float64))))) > 32

    if backend.is_stub:
        after = _stub_request_counts(backend)
        assert all(after[name] == before[name] + 1 for name in before)
