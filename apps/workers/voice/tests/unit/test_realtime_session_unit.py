import asyncio
import base64
import io
import json
import time

import httpx
import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient
from fastrtc import ReplyOnPause
from fastrtc.utils import Context, current_channel, current_context
from shared.inference_client import InferenceClient, InferenceEndpoint
from shared.worker_voice import MAX_HISTORY_MESSAGES, SAMPLE_RATE, SessionTokens, build_app

AUTH_TOKEN = "realtime-test-auth-token"


def make_wav(samples: np.ndarray | None = None) -> bytes:
    if samples is None:
        duration = 0.5
        samples = (
            0.2
            * np.sin(
                2 * np.pi * 440 * np.arange(int(SAMPLE_RATE * duration)) / SAMPLE_RATE
            )
        ).astype(np.float32)
    buffer = io.BytesIO()
    sf.write(buffer, samples, SAMPLE_RATE, format="WAV", subtype="PCM_16")
    return buffer.getvalue()


class StubInferenceClient:
    def __init__(self) -> None:
        self.fail_stage: str | None = None
        self.transcriptions = 0
        self.messages: list[list[dict[str, str]]] = []

    def transcribe(self, audio: bytes, filename: str) -> str:
        self.transcriptions += 1
        samples, sample_rate = sf.read(io.BytesIO(audio), dtype="float32")
        assert sample_rate == SAMPLE_RATE
        assert samples.ndim == 1
        if self.fail_stage == "stt":
            raise RuntimeError("stub transcription failure")
        return "fixture transcript"

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.messages.append(messages)
        if self.fail_stage == "llm":
            raise RuntimeError("stub completion failure")
        return "fixture reply"

    def speak(self, text: str) -> tuple[bytes, int]:
        if self.fail_stage == "tts":
            raise RuntimeError("stub speech failure")
        return make_wav(), SAMPLE_RATE


class StubDataChannel:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def send(self, message: str) -> None:
        self.messages.append(message)


async def stub_turn_credentials() -> dict[str, object]:
    return {
        "iceServers": [
            {
                "urls": ["turn:stub.example.com:3478"],
                "username": "stub-user",
                "credential": "stub-credential",
            }
        ]
    }


@pytest.fixture
def worker():
    inference = StubInferenceClient()
    app = build_app(
        inference_client=inference,
        client_secret_auth_token=AUTH_TOKEN,
        turn_credentials_provider=stub_turn_credentials,
    )
    with TestClient(app) as client:
        yield client, app, inference


def test_authentication_and_ephemeral_session(worker):
    client, _, _ = worker
    missing = client.post("/v1/realtime/client_secrets", json={"session": {}})
    invalid = client.post(
        "/v1/realtime/client_secrets",
        headers={"Authorization": "Bearer invalid"},
        json={"session": {}},
    )
    assert missing.status_code == invalid.status_code == 401

    response = client.post(
        "/v1/realtime/client_secrets",
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        json={"session": {}},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["expires_at"] - int(time.time()) in (59, 60)
    assert result["rtc_configuration"]["iceServers"][0]["urls"][0].startswith("turn:")
    rejected_call = client.post(
        "/v1/realtime/calls",
        headers={"Authorization": "Bearer invalid"},
        data={"sdp": "invalid"},
    )
    assert rejected_call.status_code == 401


def test_session_tokens_expire(monkeypatch):
    now = 1_000.0
    monkeypatch.setattr("shared.worker_voice.time.time", lambda: now)
    tokens = SessionTokens()
    token, expires_at = tokens.create()
    assert expires_at == 1_060
    assert tokens.validate(token)
    monkeypatch.setattr("shared.worker_voice.time.time", lambda: 1_060.0)
    assert not tokens.validate(token)


def process_turn(app, session_id: str, samples: np.ndarray, channel: StubDataChannel):
    async def run():
        context_token = current_context.set(Context(webrtc_id=session_id))
        channel_token = current_channel.set(channel)
        try:
            return [
                item
                async for item in app.state.turn_handler((SAMPLE_RATE, samples))
            ]
        finally:
            await asyncio.sleep(0.01)
            current_channel.reset(channel_token)
            current_context.reset(context_token)

    return asyncio.run(run())


def test_build_app_handler_audio_history_failure_and_cleanup(worker):
    _, app, inference = worker
    assert isinstance(app.state.stream.event_handler, ReplyOnPause)
    samples = np.full(SAMPLE_RATE // 2, 5_000, dtype=np.int16)
    channel = StubDataChannel()

    result = process_turn(app, "session-a", samples, channel)
    assert len(result) == 1
    output_rate, output_audio = result[0]
    assert output_rate == SAMPLE_RATE
    assert output_audio.dtype == np.int16
    output_rms = float(np.sqrt(np.mean(np.square(output_audio.astype(np.float32)))))
    assert output_rms > 32
    assert inference.messages[-1][-1] == {
        "role": "user",
        "content": "fixture transcript",
    }

    process_turn(app, "session-b", samples, channel)
    second_session_history = inference.messages[-1]
    assert [message["role"] for message in second_session_history] == ["system", "user"]
    assert all("fixture reply" not in message["content"] for message in second_session_history)

    for _ in range(MAX_HISTORY_MESSAGES):
        process_turn(app, "session-a", samples, channel)
    bounded_history = app.state.histories.get("session-a")
    assert bounded_history[0]["role"] == "system"
    assert len(bounded_history) <= MAX_HISTORY_MESSAGES + 1

    app.state.stream.clean_up("session-a")
    assert app.state.histories.get("session-a") == [
        {"role": "system", "content": "You are a concise, helpful voice assistant."}
    ]


@pytest.mark.parametrize("stage", ["stt", "llm", "tts"])
def test_each_inference_failure_emits_stage_error(worker, stage, caplog):
    _, app, inference = worker
    inference.fail_stage = stage
    channel = StubDataChannel()
    samples = np.full(SAMPLE_RATE // 2, 5_000, dtype=np.int16)

    assert process_turn(app, "session", samples, channel) == []
    event = json.loads(channel.messages[-1])
    assert event == {"type": "error", "message": f"{stage} failed"}
    assert f"stage={stage}" in caplog.text


def test_invalid_audio_emits_turn_error_and_session_recovers(worker):
    _, app, inference = worker
    channel = StubDataChannel()
    silent = np.zeros(SAMPLE_RATE // 2, dtype=np.int16)
    assert process_turn(app, "session", silent, channel) == []
    assert inference.transcriptions == 0
    assert json.loads(channel.messages[-1]) == {
        "type": "error",
        "message": "stt failed",
    }

    audible = np.full(SAMPLE_RATE // 2, 5_000, dtype=np.int16)
    assert process_turn(app, "session", audible, channel)
    assert inference.transcriptions == 1


def test_inference_client_sends_history_and_decodes_tts_audio():
    wav = make_wav()
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/v1/chat/completions"):
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": "fixture reply"}},
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "audio_base64": base64.b64encode(wav).decode("ascii"),
                "format": "wav",
                "sample_rate": SAMPLE_RATE,
            },
        )

    transport = httpx.MockTransport(respond)
    endpoint = InferenceEndpoint("https://worker.example", "test-key")
    client = InferenceClient(endpoint, endpoint, endpoint, transport=transport)
    history = [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "previous turn"},
        {"role": "assistant", "content": "previous reply"},
    ]
    assert client.complete(history) == "fixture reply"
    audio, sample_rate = client.speak("next reply")

    assert json.loads(requests[0].content)["messages"] == history
    assert audio == wav
    assert sample_rate == SAMPLE_RATE
