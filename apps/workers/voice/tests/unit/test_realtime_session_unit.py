import asyncio
import functools
import io
import json
import threading
import time

import fastrtc.utils as fastrtc_utils
import httpx
import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient
from fastrtc import ReplyOnPause
from fastrtc.utils import Context, current_channel, current_context
from shared.inference_client import InferenceClient, InferenceEndpoint
from shared.worker_voice import (
    MAX_HISTORY_MESSAGES,
    SAMPLE_RATE,
    TURN_AUDIO_CHUNK_DURATION,
    TURN_SILENCE_ERROR_DURATION,
    SessionTokens,
    build_app,
)

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
        self.speech_requests: list[tuple[str, str, bytes | None]] = []
        self.stream_started = threading.Event()
        self.stream_finished = threading.Event()
        self.release_stream = threading.Event()
        self.transcription_started = threading.Event()
        self.release_transcription = threading.Event()
        self.release_stream.set()
        self.release_transcription.set()

    def transcribe(self, audio: bytes, filename: str) -> str:
        self.transcription_started.set()
        self.release_transcription.wait()
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

    def speak(
        self,
        text: str,
        voice: str,
        reference_audio: bytes | None = None,
    ) -> tuple[bytes, int]:
        self.speech_requests.append((text, voice, reference_audio))
        if self.fail_stage == "tts":
            raise RuntimeError("stub speech failure")
        return make_wav(), SAMPLE_RATE

    def stream_speak(
        self,
        text: str,
        voice: str,
        reference_audio: bytes | None = None,
    ):
        self.speech_requests.append((text, voice, reference_audio))
        if self.fail_stage == "tts":
            raise RuntimeError("stub speech failure")
        self.stream_started.set()
        yield np.array([5000, -5000], dtype=np.int16)
        self.release_stream.wait(timeout=2)
        self.stream_finished.set()
        yield np.array([3000, -3000], dtype=np.int16)


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
    assert result["session"]["voice"] == "alloy"
    assert result["rtc_configuration"]["iceServers"][0]["urls"][0].startswith("turn:")
    rejected_call = client.post(
        "/v1/realtime/calls",
        headers={"Authorization": "Bearer invalid"},
        data={"sdp": "invalid"},
    )
    assert rejected_call.status_code == 401


def test_secret_huggingface_token_authenticates_hub_and_turn(monkeypatch):
    token = "hf-sentinel"
    calls: dict[str, object] = {}
    monkeypatch.setenv("SECRET_HUGGINGFACE_TOKEN", token)

    def login(*, token: str, add_to_git_credential: bool) -> None:
        calls["login"] = (token, add_to_git_credential)

    async def turn_credentials(*, hf_token: str, ttl: int) -> dict[str, object]:
        calls["turn"] = (hf_token, ttl)
        return await stub_turn_credentials()

    monkeypatch.setattr("huggingface_hub.login", login)
    monkeypatch.setattr("fastrtc.get_cloudflare_turn_credentials_async", turn_credentials)
    app = build_app(
        inference_client=StubInferenceClient(),
        client_secret_auth_token=AUTH_TOKEN,
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/realtime/client_secrets",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            json={"session": {}},
        )

    assert response.status_code == 200
    assert calls["login"] == (token, False)
    assert calls["turn"] == (token, 600)


@pytest.mark.parametrize("requested_voice", [None, "alloy"])
def test_client_secret_normalizes_default_voice(worker, requested_voice):
    client, _, _ = worker
    response = client.post(
        "/v1/realtime/client_secrets",
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        json={"session": {"voice": requested_voice}},
    )
    assert response.status_code == 200
    assert response.json()["session"]["voice"] == "alloy"


def test_reference_voice_is_resolved_from_manifest(worker, monkeypatch, tmp_path):
    import shared.worker_voice as worker_voice

    reference_audio = make_wav()
    (tmp_path / "GUT.wav").write_bytes(reference_audio)
    (tmp_path / "voices.json").write_text(
        json.dumps(
            [
                {
                    "path": "GUT.wav",
                    "name": "GUT",
                    "prompt": "Use the GUT persona.",
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(worker_voice, "REFERENCE_VOICES_DIR", tmp_path)

    assert worker_voice.resolve_voice("GUT") == (
        "GUT",
        "Use the GUT persona.",
        reference_audio,
    )


def test_missing_reference_voice_falls_back_to_alloy(worker, monkeypatch, tmp_path):
    import shared.worker_voice as worker_voice

    monkeypatch.setattr(worker_voice, "REFERENCE_VOICES_DIR", tmp_path)
    assert worker_voice.resolve_voice("GUT") == (
        "alloy",
        "You are a concise, helpful voice assistant.",
        None,
    )


def test_run_turn_forwards_selected_reference_to_tts(worker, monkeypatch, tmp_path):
    import shared.worker_voice as worker_voice

    reference_audio = make_wav()
    (tmp_path / "GUT.wav").write_bytes(reference_audio)
    (tmp_path / "voices.json").write_text(
        json.dumps([{"path": "GUT.wav", "name": "GUT", "prompt": "GUT persona"}]),
        encoding="utf-8",
    )
    monkeypatch.setattr(worker_voice, "REFERENCE_VOICES_DIR", tmp_path)
    voice, system_message, resolved_audio = worker_voice.resolve_voice("GUT")
    _, _, inference = worker

    transcript, reply = worker_voice.run_turn(
        np.full(SAMPLE_RATE // 2, 5_000, dtype=np.int16),
        SAMPLE_RATE,
        inference,
        [{"role": "system", "content": system_message}],
    )
    list(inference.stream_speak(reply, voice, resolved_audio))

    assert transcript == "fixture transcript"
    assert inference.speech_requests[-1][1:] == ("GUT", reference_audio)


def test_session_tokens_expire(monkeypatch):
    now = 1_000.0
    monkeypatch.setattr("shared.worker_voice.time.time", lambda: now)
    tokens = SessionTokens()
    token, expires_at = tokens.create()
    assert expires_at == 1_060
    assert tokens.validate(token)
    monkeypatch.setattr("shared.worker_voice.time.time", lambda: 1_060.0)
    assert not tokens.validate(token)


def test_session_tokens_retain_effective_voice():
    tokens = SessionTokens()
    token, _ = tokens.create("alloy")
    assert tokens.voice(token) == "alloy"


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
    handler = app.state.stream.event_handler
    assert isinstance(handler, ReplyOnPause)
    assert app.state.stream.concurrency_limit == 2
    assert handler.can_interrupt is False
    silence = np.zeros(int(SAMPLE_RATE * TURN_AUDIO_CHUNK_DURATION), dtype=np.int16)
    assert handler.determine_pause(silence, SAMPLE_RATE, handler.state.new())
    samples = np.full(SAMPLE_RATE // 2, 5_000, dtype=np.int16)
    channel = StubDataChannel()

    result = process_turn(app, "session-a", samples, channel)
    assert len(result) == 2
    assert all(output_rate == SAMPLE_RATE for output_rate, _ in result)
    assert all(output_audio.dtype == np.int16 for _, output_audio in result)
    assert all(output_audio.ndim == 2 and output_audio.shape[0] == 1 for _, output_audio in result)
    output_audio = np.concatenate([audio for _, audio in result], axis=1)
    output_rms = float(np.sqrt(np.mean(np.square(output_audio.astype(np.float32)))))
    assert output_rms > 32
    assert inference.messages[-1][-1] == {
        "role": "user",
        "content": "fixture transcript",
    }
    assert inference.speech_requests[-1][1:] == ("alloy", None)

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


def test_handler_emits_audio_before_tts_generation_finishes(worker):
    _, app, inference = worker
    samples = np.full(SAMPLE_RATE // 2, 5_000, dtype=np.int16)
    inference.stream_started.clear()
    inference.stream_finished.clear()
    inference.release_stream.clear()

    async def run():
        context_token = current_context.set(Context(webrtc_id="stream-session"))
        channel = StubDataChannel()
        channel_token = current_channel.set(channel)
        try:
            handler = app.state.turn_handler((SAMPLE_RATE, samples))
            first_rate, first_audio = await anext(handler)
            assert first_rate == SAMPLE_RATE
            assert first_audio.dtype == np.int16
            assert first_audio.shape == (1, 2)
            assert inference.stream_started.is_set()
            assert not inference.stream_finished.is_set()
            inference.release_stream.set()
            remaining = [chunk async for chunk in handler]
            assert len(remaining) == 1
        finally:
            current_channel.reset(channel_token)
            current_context.reset(context_token)

    asyncio.run(run())


def test_handler_yields_heartbeat_while_inference_is_pending(worker, monkeypatch):
    _, app, inference = worker
    monkeypatch.setattr("shared.worker_voice.TURN_HEARTBEAT_SECONDS", 0.01)
    inference.release_transcription.clear()
    samples = np.full(SAMPLE_RATE // 2, 5_000, dtype=np.int16)

    async def run():
        context_token = current_context.set(Context(webrtc_id="heartbeat-session"))
        channel_token = current_channel.set(StubDataChannel())
        handler = app.state.turn_handler((SAMPLE_RATE, samples))
        try:
            frame = await asyncio.wait_for(anext(handler), timeout=1)
            inference.release_transcription.set()
            await asyncio.wait_for(anext(handler), timeout=1)
            return frame
        finally:
            await handler.aclose()
            inference.release_transcription.set()
            current_channel.reset(channel_token)
            current_context.reset(context_token)

    sample_rate, silence = asyncio.run(run())

    assert sample_rate == SAMPLE_RATE and silence.dtype == np.int16 and not silence.any()


def test_player_worker_decode_does_not_retry_an_inflight_emit(monkeypatch):
    active_calls = 0
    max_active_calls = 0
    call_lock = threading.Lock()
    quit_event = asyncio.Event()
    queue = asyncio.Queue()
    original_wait_for = asyncio.wait_for

    def emit():
        nonlocal active_calls, max_active_calls
        with call_lock:
            active_calls += 1
            max_active_calls = max(max_active_calls, active_calls)
        try:
            time.sleep(0.05)
            return SAMPLE_RATE, np.ones((1, 480), dtype=np.int16)
        finally:
            with call_lock:
                active_calls -= 1

    async def short_watchdog(awaitable, timeout=None):
        return await original_wait_for(awaitable, timeout=0.01 if timeout == 60 else timeout)

    async def run():
        monkeypatch.setattr(fastrtc_utils.asyncio, "wait_for", short_watchdog)
        next_frame = functools.partial(
            asyncio.get_running_loop().run_in_executor, None, emit
        )
        decoder = asyncio.create_task(
            fastrtc_utils.player_worker_decode(
                next_frame,
                queue,
                quit_event,
                channel=None,
                set_additional_outputs=None,
                sample_rate=SAMPLE_RATE,
                frame_size=480,
            )
        )
        try:
            frame = await asyncio.wait_for(queue.get(), timeout=1)
            quit_event.set()
            await decoder
            return frame
        finally:
            quit_event.set()
            if not decoder.done():
                decoder.cancel()
                await asyncio.gather(decoder, return_exceptions=True)

    frame = asyncio.run(run())

    assert max_active_calls == 1 and frame.samples == 480


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
    if stage == "tts":
        assert "stub speech failure" in caplog.text


def test_invalid_audio_emits_turn_error_and_session_recovers(worker):
    _, app, inference = worker
    channel = StubDataChannel()
    silent = np.zeros(SAMPLE_RATE // 2, dtype=np.int16)
    assert process_turn(app, "session", silent, channel) == []
    assert not channel.messages
    continued_silence = np.zeros(
        int(SAMPLE_RATE * (TURN_SILENCE_ERROR_DURATION - 0.5)), dtype=np.int16
    )
    assert process_turn(app, "session", continued_silence, channel) == []
    assert inference.transcriptions == 0
    assert json.loads(channel.messages[-1]) == {
        "type": "error",
        "message": "stt failed",
    }

    audible = np.full(SAMPLE_RATE // 2, 5_000, dtype=np.int16)
    assert process_turn(app, "session", audible, channel)
    assert inference.transcriptions == 1


def test_inference_client_sends_history_to_llm():
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.extensions["timeout"]["read"] == 120.0
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "fixture reply"}}]},
        )

    endpoint = InferenceEndpoint("https://worker.example", "test-key")
    client = InferenceClient(
        endpoint, endpoint, endpoint, transport=httpx.MockTransport(respond)
    )
    history = [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "previous turn"},
        {"role": "assistant", "content": "previous reply"},
    ]

    assert client.complete(history) == "fixture reply"
    assert json.loads(requests[0].content)["messages"] == history


def test_inference_client_streams_with_tts_read_timeout():
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.extensions["timeout"]["read"] == 120.0
        return httpx.Response(
            200,
            headers={"X-Sample-Rate": str(SAMPLE_RATE)},
            content=np.array([100], dtype="<i2").tobytes(),
        )

    endpoint = InferenceEndpoint("https://worker.example", "test-key")
    client = InferenceClient(
        endpoint, endpoint, endpoint, transport=httpx.MockTransport(respond)
    )

    chunks = list(client.stream_speak("reply", "alloy"))

    assert len(chunks) == 1


def test_inference_client_streams_pcm_chunks():
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            headers={"X-Sample-Rate": str(SAMPLE_RATE)},
            content=np.array([100, -100, 200], dtype="<i2").tobytes(),
        )

    endpoint = InferenceEndpoint("https://worker.example", "test-key")
    client = InferenceClient(
        endpoint,
        endpoint,
        endpoint,
        transport=httpx.MockTransport(respond),
    )

    chunks = list(client.stream_speak("reply", "alloy"))

    assert len(chunks) == 1
    np.testing.assert_array_equal(chunks[0], np.array([100, -100, 200], dtype=np.int16))
    assert requests[0].url.path == "/v1/audio/speech/stream"
    assert requests[0].headers["authorization"] == "Bearer test-key"
    assert json.loads(requests[0].content)["input"] == "reply"
