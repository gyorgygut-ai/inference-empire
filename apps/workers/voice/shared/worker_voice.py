from __future__ import annotations

import asyncio
import hmac
import io
import json
import logging
import os
import queue
import secrets
import threading
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

import numpy as np
from dist.contract_voice import ClientSecretInput, ClientSecretOutput, RealtimeSession
from fastapi import FastAPI, HTTPException, Request, Response

from shared.inference_client import InferenceClient

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

SAMPLE_RATE = 24_000
TOKEN_TTL_SECONDS = 60
MAX_HISTORY_MESSAGES = 20
DEFAULT_VOICE = "alloy"
REFERENCE_VOICES_DIR = Path(
    os.environ.get(
        "VOICE_REFERENCES_DIR",
        str(Path(__file__).resolve().parents[1] / "references"),
    )
).resolve()
TURN_AUDIO_CHUNK_DURATION = 0.3
# Let silence reach on_turn so the existing audio validator can emit its error.
TURN_STARTED_TALKING_THRESHOLD = -0.001
TURN_SPEECH_THRESHOLD = 0.1
TURN_HEARTBEAT_SECONDS = 15
TURN_SILENCE_ERROR_DURATION = 1.9
TURN_ACTIVE_AUDIO_RMS_THRESHOLD = 0.005
SYSTEM_MESSAGE = "You are a concise, helpful voice assistant."
logger = logging.getLogger(__name__)


class InferencePipeline(Protocol):
    def transcribe(self, audio: bytes, filename: str) -> str: ...

    def complete(self, messages: list[dict[str, str]]) -> str: ...

    def stream_speak(
        self,
        text: str,
        voice: str,
        reference_audio: bytes | None = None,
    ) -> Iterator[np.ndarray]: ...


class TurnError(Exception):
    def __init__(self, stage: str, reason: str):
        super().__init__(reason)
        self.stage = stage


class SessionTokens:
    def __init__(self, ttl_seconds: int = TOKEN_TTL_SECONDS):
        self.ttl_seconds = ttl_seconds
        self._tokens: dict[str, tuple[float, str]] = {}

    def create(self, voice: str = DEFAULT_VOICE) -> tuple[str, int]:
        expires_at = int(time.time()) + self.ttl_seconds
        token = secrets.token_urlsafe(32)
        self._tokens[token] = (float(expires_at), voice)
        return token, expires_at

    def validate(self, token: str) -> bool:
        entry = self._tokens.get(token)
        if entry is None:
            return False
        expires_at, _ = entry
        if expires_at <= time.time():
            del self._tokens[token]
            return False
        return True

    def voice(self, token: str) -> str | None:
        entry = self._tokens.get(token)
        if entry is None or entry[0] <= time.time():
            return None
        return entry[1]


class SessionHistories:
    def __init__(self) -> None:
        self._histories: dict[str, list[dict[str, str]]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def get(
        self,
        session_id: str,
        system_message: str = SYSTEM_MESSAGE,
    ) -> list[dict[str, str]]:
        return list(
            self._histories.get(
                session_id, [{"role": "system", "content": system_message}]
            )
        )

    def lock(self, session_id: str) -> asyncio.Lock:
        return self._locks.setdefault(session_id, asyncio.Lock())

    def append(
        self,
        session_id: str,
        transcript: str,
        reply: str,
        system_message: str = SYSTEM_MESSAGE,
    ) -> None:
        history = self.get(session_id, system_message)
        history.extend(
            [
                {"role": "user", "content": transcript},
                {"role": "assistant", "content": reply},
            ]
        )
        self._histories[session_id] = [history[0], *history[1:][-MAX_HISTORY_MESSAGES:]]

    def remove(self, session_id: str) -> None:
        self._histories.pop(session_id, None)
        self._locks.pop(session_id, None)


def _wav_bytes(audio: np.ndarray) -> bytes:
    import soundfile as sf

    buffer = io.BytesIO()
    sf.write(buffer, audio, SAMPLE_RATE, format="WAV", subtype="PCM_16")
    return buffer.getvalue()


def resolve_voice(voice: str | None) -> tuple[str, str, bytes | None]:
    requested = (voice or DEFAULT_VOICE).strip()
    if not requested or requested.casefold() == DEFAULT_VOICE:
        return DEFAULT_VOICE, SYSTEM_MESSAGE, None

    manifest = REFERENCE_VOICES_DIR / "voices.json"
    if not manifest.is_file():
        return DEFAULT_VOICE, SYSTEM_MESSAGE, None
    try:
        entries = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.exception("Unable to read reference voice manifest")
        return DEFAULT_VOICE, SYSTEM_MESSAGE, None

    if not isinstance(entries, list):
        return DEFAULT_VOICE, SYSTEM_MESSAGE, None
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        filename = entry.get("path")
        if (
            not isinstance(name, str)
            or not isinstance(filename, str)
            or Path(filename).name != filename
            or name.casefold() != requested.casefold()
        ):
            continue
        reference_path = REFERENCE_VOICES_DIR / filename
        try:
            reference_audio = reference_path.read_bytes()
        except OSError:
            return DEFAULT_VOICE, SYSTEM_MESSAGE, None
        prompt = entry.get("prompt")
        system_message = prompt if isinstance(prompt, str) and prompt.strip() else SYSTEM_MESSAGE
        return name, system_message, reference_audio
    return DEFAULT_VOICE, SYSTEM_MESSAGE, None


def _float_audio(audio: np.ndarray) -> np.ndarray:
    samples = np.asarray(audio)
    if samples.ndim > 1:
        if samples.shape[0] == 1:
            samples = samples.reshape(-1)
        elif samples.shape[-1] == 1:
            samples = samples.reshape(-1)
        else:
            raise TurnError("stt", "input audio must be mono")
    samples = samples.reshape(-1)
    if samples.dtype == np.int16:
        values = samples.astype(np.float32) / 32768.0
    else:
        values = samples.astype(np.float32)
    if values.size == 0 or not np.isfinite(values).all():
        raise TurnError("stt", "input audio is empty or invalid")
    if float(np.max(np.abs(values))) < 0.005:
        raise TurnError("stt", "input audio is silent")
    return values


def run_turn(
    audio: np.ndarray,
    sample_rate: int,
    client: InferencePipeline,
    history: list[dict[str, str]],
) -> tuple[str, str]:
    if sample_rate != SAMPLE_RATE:
        raise TurnError("stt", "input sample rate is not 24 kHz")
    samples = _float_audio(audio)
    try:
        transcript = client.transcribe(_wav_bytes(samples), "audio.wav")
        if not transcript.strip():
            raise ValueError("empty transcript")
    except Exception as error:
        raise TurnError("stt", "transcription failed") from error

    messages = [*history, {"role": "user", "content": transcript}]
    try:
        reply = client.complete(messages)
        if not reply.strip():
            raise ValueError("empty reply")
    except Exception as error:
        raise TurnError("llm", "completion failed") from error

    return transcript, reply


def build_app(
    inference_client: InferencePipeline | None = None,
    token_store: SessionTokens | None = None,
    client_secret_auth_token: str | None = None,
    turn_credentials_provider: Callable[[], Any] | None = None,
) -> FastAPI:
    from fastrtc import (
        AlgoOptions,
        ReplyOnPause,
        Stream,
        WebRTCError,
        get_cloudflare_turn_credentials,
        get_cloudflare_turn_credentials_async,
        get_current_context,
    )
    from fastrtc.stream import Body

    client = inference_client if inference_client is not None else InferenceClient.from_env()
    tokens = token_store if token_store is not None else SessionTokens()
    trusted_server_token = client_secret_auth_token or os.environ.get(
        "SECRET_VOICE_WORKER_AUTH_TOKEN"
    )
    huggingface_token = os.environ.get("SECRET_HUGGINGFACE_TOKEN")
    if turn_credentials_provider is None:
        if not huggingface_token:
            raise RuntimeError("SECRET_HUGGINGFACE_TOKEN is required for TURN credentials")
        from huggingface_hub import login

        login(token=huggingface_token, add_to_git_credential=False)

    server_turn_configuration = (
        get_cloudflare_turn_credentials(hf_token=huggingface_token, ttl=360_000)
        if turn_credentials_provider is None
        else None
    )

    async def get_turn_configuration() -> dict[str, Any]:
        if turn_credentials_provider is not None:
            return await turn_credentials_provider()
        return await get_cloudflare_turn_credentials_async(
            hf_token=huggingface_token,
            ttl=600,
        )

    histories = SessionHistories()
    session_voices: dict[str, str] = {}
    quiet_turn_audio: dict[str, np.ndarray] = {}
    heartbeat = np.zeros((1, SAMPLE_RATE // 10), dtype=np.int16)

    async def wait_with_heartbeat(task: asyncio.Task[Any]):
        while not task.done():
            done, _ = await asyncio.wait(
                {task}, timeout=TURN_HEARTBEAT_SECONDS
            )
            if not done:
                yield SAMPLE_RATE, heartbeat

    async def on_turn(audio: tuple[int, np.ndarray]):
        session_id = get_current_context().webrtc_id
        sample_rate, samples = audio
        lock = histories.lock(session_id)
        voice_name, system_message, reference_audio = await asyncio.to_thread(
            resolve_voice,
            session_voices.get(session_id),
        )
        try:
            async with lock:
                samples = np.asarray(samples).reshape(-1)
                pending_audio = quiet_turn_audio.get(session_id)
                if pending_audio is not None:
                    samples = np.concatenate((pending_audio, samples))

                normalized_samples = samples.astype(np.float32)
                if samples.dtype == np.int16:
                    normalized_samples /= 32768.0
                input_rms = float(
                    np.sqrt(np.mean(np.square(normalized_samples, dtype=np.float64)))
                )
                if input_rms < TURN_ACTIVE_AUDIO_RMS_THRESHOLD:
                    if samples.size / sample_rate < TURN_SILENCE_ERROR_DURATION:
                        quiet_turn_audio[session_id] = samples.copy()
                        return
                    quiet_turn_audio.pop(session_id, None)
                    raise TurnError("stt", "input audio is silent")
                quiet_turn_audio.pop(session_id, None)

                turn_task = asyncio.create_task(
                    asyncio.to_thread(
                        run_turn,
                        samples,
                        sample_rate,
                        client,
                        histories.get(session_id, system_message),
                    )
                )
                logger.info("realtime turn inference started")
                async for frame in wait_with_heartbeat(turn_task):
                    yield frame
                transcript, reply = await turn_task
                logger.info("realtime turn inference completed")
                audio_queue: queue.Queue[tuple[str, Any]] = queue.Queue(maxsize=1)
                stop_stream = threading.Event()

                def send_stream_item(item: tuple[str, Any]) -> bool:
                    while not stop_stream.is_set():
                        try:
                            audio_queue.put(item, timeout=0.1)
                            return True
                        except queue.Full:
                            continue
                    return False

                def produce_audio() -> None:
                    try:
                        for chunk in client.stream_speak(
                            reply, voice_name, reference_audio
                        ):
                            if not send_stream_item(("chunk", chunk)):
                                return
                    except Exception as error:
                        send_stream_item(("error", error))
                    finally:
                        send_stream_item(("done", None))

                producer_task = asyncio.create_task(asyncio.to_thread(produce_audio))
                logger.info("realtime turn speech stream started")
                total_square_sum = 0.0
                total_samples = 0
                audible = False
                while True:
                    try:
                        item_type, chunk = await asyncio.to_thread(
                            audio_queue.get, True, TURN_HEARTBEAT_SECONDS
                        )
                    except queue.Empty:
                        yield SAMPLE_RATE, heartbeat
                        continue
                    if item_type == "done":
                        break
                    if item_type == "error":
                        if isinstance(chunk, Exception):
                            raise chunk
                        raise RuntimeError("TTS stream failed")
                    chunk_samples = np.asarray(chunk)
                    if (
                        chunk_samples.dtype != np.int16
                        or chunk_samples.ndim != 1
                        or chunk_samples.size == 0
                    ):
                        raise ValueError("TTS stream returned invalid audio chunk")
                    if not np.isfinite(chunk_samples).all():
                        raise ValueError("TTS stream returned non-finite audio")
                    if float(np.max(np.abs(chunk_samples.astype(np.float32)))) < 32:
                        continue
                    audible = True
                    total_square_sum += float(
                        np.sum(np.square(chunk_samples.astype(np.float64)))
                    )
                    total_samples += chunk_samples.size
                    yield SAMPLE_RATE, chunk_samples.reshape(1, -1)
                await producer_task
                if not audible:
                    raise ValueError("TTS stream returned empty or silent audio")
                logger.info("realtime turn speech stream completed samples=%d", total_samples)
                histories.append(session_id, transcript, reply, system_message)
        except TurnError as error:
            logger.exception("realtime turn failed stage=%s reason=%s", error.stage, error)
            WebRTCError(f"{error.stage} failed")
            return
        except Exception:
            logger.exception("realtime turn failed stage=tts reason=speech synthesis failed")
            WebRTCError("tts failed")
            return
        finally:
            if "stop_stream" in locals():
                stop_stream.set()
        logger.info(
            "realtime turn completed transcript_chars=%d response_chars=%d output_rms=%.6f",
            len(transcript),
            len(reply),
            float(np.sqrt(total_square_sum / total_samples)),
        )

    reply_handler = ReplyOnPause(
        on_turn,
        algo_options=AlgoOptions(
            audio_chunk_duration=TURN_AUDIO_CHUNK_DURATION,
            started_talking_threshold=TURN_STARTED_TALKING_THRESHOLD,
            speech_threshold=TURN_SPEECH_THRESHOLD,
        ),
        can_interrupt=False,
        expected_layout="mono",
        input_sample_rate=SAMPLE_RATE,
        output_sample_rate=SAMPLE_RATE,
    )

    class SessionStream(Stream):
        def clean_up(self, webrtc_id: str):
            histories.remove(webrtc_id)
            session_voices.pop(webrtc_id, None)
            quiet_turn_audio.pop(webrtc_id, None)
            return super().clean_up(webrtc_id)

    stream = SessionStream(
        handler=reply_handler,
        modality="audio",
        mode="send-receive",
        concurrency_limit=2,
        rtc_configuration=get_turn_configuration,
        server_rtc_configuration=server_turn_configuration,
    )
    app = FastAPI(title="worker-voice")
    app.state.stream = stream
    app.state.turn_handler = on_turn
    app.state.histories = histories

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/realtime/client_secrets", response_model=ClientSecretOutput)
    async def create_client_secret(
        request: ClientSecretInput, http_request: Request, response: Response
    ) -> ClientSecretOutput:
        authorization = http_request.headers.get("authorization", "")
        scheme, _, supplied_token = authorization.partition(" ")
        if not trusted_server_token:
            raise HTTPException(status_code=503, detail="Session authentication is not configured")
        if scheme.casefold() != "bearer" or not hmac.compare_digest(
            supplied_token.encode(), trusted_server_token.encode()
        ):
            raise HTTPException(status_code=401, detail="Invalid server credential")
        try:
            rtc_configuration = await stream.resolve_rtc_configuration()
        except Exception as error:
            logger.exception("Unable to create TURN credentials")
            raise HTTPException(
                status_code=503,
                detail="TURN credentials are unavailable",
            ) from error
        requested_voice = request.session.voice if request.session is not None else None
        voice_name, _, _ = await asyncio.to_thread(resolve_voice, requested_voice)
        token, expires_at = tokens.create(voice_name)
        response.headers["Cache-Control"] = "no-store"
        session = request.session or RealtimeSession()
        session = session.model_copy(update={"voice": voice_name})
        return ClientSecretOutput(
            value=token,
            expires_at=expires_at,
            session=session,
            rtc_configuration=rtc_configuration,
        )

    @app.post("/v1/realtime/calls")
    async def realtime_call(request: Request) -> Response:
        authorization = request.headers.get("authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.casefold() != "bearer" or not tokens.validate(token):
            raise HTTPException(status_code=401, detail="Invalid or expired session token")
        form = await request.form()
        sdp = form.get("sdp")
        if not isinstance(sdp, str) or not sdp.strip():
            raise HTTPException(status_code=422, detail="sdp is required")
        webrtc_id = uuid.uuid4().hex
        voice_name = tokens.voice(token)
        if voice_name is None:
            raise HTTPException(status_code=401, detail="Invalid or expired session token")
        session_voices[webrtc_id] = voice_name
        body = Body(sdp=sdp, type="offer", webrtc_id=webrtc_id)
        try:
            answer = await stream.offer(body)
        except Exception as error:
            session_voices.pop(webrtc_id, None)
            logger.exception("WebRTC offer negotiation failed")
            raise HTTPException(
                status_code=502,
                detail="WebRTC offer negotiation failed",
            ) from error
        if not isinstance(answer, dict) or not isinstance(answer.get("sdp"), str):
            raise HTTPException(status_code=502, detail="WebRTC negotiation returned an invalid answer")
        return Response(content=answer["sdp"], media_type="application/sdp")

    return app
