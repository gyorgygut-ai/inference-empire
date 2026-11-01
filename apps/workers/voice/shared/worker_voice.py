from __future__ import annotations

import asyncio
import hmac
import io
import logging
import os
import secrets
import time
import uuid
from typing import TYPE_CHECKING, Any, Protocol

import numpy as np
import soundfile as sf
from dist.contract_voice import ClientSecretInput, ClientSecretOutput, RealtimeSession
from fastapi import FastAPI, HTTPException, Request, Response

from shared.inference_client import InferenceClient

if TYPE_CHECKING:
    from collections.abc import Callable

SAMPLE_RATE = 24_000
TOKEN_TTL_SECONDS = 60
MAX_HISTORY_MESSAGES = 20
TURN_AUDIO_CHUNK_DURATION = 0.3
TURN_STARTED_TALKING_THRESHOLD = 0.1
TURN_SPEECH_THRESHOLD = 0.1
SYSTEM_MESSAGE = "You are a concise, helpful voice assistant."
logger = logging.getLogger(__name__)


class InferencePipeline(Protocol):
    def transcribe(self, audio: bytes, filename: str) -> str: ...

    def complete(self, messages: list[dict[str, str]]) -> str: ...

    def speak(self, text: str) -> tuple[bytes, int]: ...


class TurnError(Exception):
    def __init__(self, stage: str, reason: str):
        super().__init__(reason)
        self.stage = stage


class SessionTokens:
    def __init__(self, ttl_seconds: int = TOKEN_TTL_SECONDS):
        self.ttl_seconds = ttl_seconds
        self._tokens: dict[str, float] = {}

    def create(self) -> tuple[str, int]:
        expires_at = int(time.time()) + self.ttl_seconds
        token = secrets.token_urlsafe(32)
        self._tokens[token] = float(expires_at)
        return token, expires_at

    def validate(self, token: str) -> bool:
        expires_at = self._tokens.get(token)
        if expires_at is None:
            return False
        if expires_at <= time.time():
            del self._tokens[token]
            return False
        return True


class SessionHistories:
    def __init__(self) -> None:
        self._histories: dict[str, list[dict[str, str]]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def get(self, session_id: str) -> list[dict[str, str]]:
        return list(
            self._histories.get(
                session_id, [{"role": "system", "content": SYSTEM_MESSAGE}]
            )
        )

    def lock(self, session_id: str) -> asyncio.Lock:
        return self._locks.setdefault(session_id, asyncio.Lock())

    def append(self, session_id: str, transcript: str, reply: str) -> None:
        history = self.get(session_id)
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
    buffer = io.BytesIO()
    sf.write(buffer, audio, SAMPLE_RATE, format="WAV", subtype="PCM_16")
    return buffer.getvalue()


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
) -> tuple[str, str, np.ndarray]:
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

    try:
        wav_bytes, output_rate = client.speak(reply)
        decoded, decoded_rate = sf.read(
            io.BytesIO(wav_bytes), dtype="float32", always_2d=True
        )
        if output_rate != SAMPLE_RATE or decoded_rate != SAMPLE_RATE:
            raise ValueError("TTS audio must be 24 kHz")
        if decoded.shape[1] != 1 or decoded.shape[0] == 0:
            raise ValueError("TTS audio must be non-empty mono audio")
        mono = decoded[:, 0]
        if not np.isfinite(mono).all() or float(np.max(np.abs(mono))) < 0.001:
            raise ValueError("TTS audio is invalid or silent")
        output = np.clip(mono, -1.0, 1.0)
        return transcript, reply, (output * 32767).astype(np.int16)
    except Exception as error:
        raise TurnError("tts", "speech synthesis failed") from error


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
    if turn_credentials_provider is None and not huggingface_token:
        raise RuntimeError("SECRET_HUGGINGFACE_TOKEN is required for TURN credentials")

    async def get_turn_configuration() -> dict[str, Any]:
        if turn_credentials_provider is not None:
            return await turn_credentials_provider()
        return await get_cloudflare_turn_credentials_async(
            hf_token=huggingface_token,
            ttl=600,
        )

    histories = SessionHistories()

    async def on_turn(audio: tuple[int, np.ndarray]):
        session_id = get_current_context().webrtc_id
        sample_rate, samples = audio
        lock = histories.lock(session_id)
        try:
            async with lock:
                transcript, reply, output = await asyncio.to_thread(
                    run_turn,
                    np.asarray(samples),
                    sample_rate,
                    client,
                    histories.get(session_id),
                )
                histories.append(session_id, transcript, reply)
        except TurnError as error:
            logger.error("realtime turn failed stage=%s reason=%s", error.stage, error)
            WebRTCError(f"{error.stage} failed")
            return
        except Exception as error:
            logger.exception("realtime turn failed stage=llm reason=%s", error)
            WebRTCError("llm failed")
            return
        logger.info(
            "realtime turn completed transcript_chars=%d response_chars=%d output_rms=%.6f",
            len(transcript),
            len(reply),
            float(np.sqrt(np.mean(np.square(output.astype(np.float32))))),
        )
        yield SAMPLE_RATE, output

    reply_handler = ReplyOnPause(
        on_turn,
        algo_options=AlgoOptions(
            audio_chunk_duration=TURN_AUDIO_CHUNK_DURATION,
            started_talking_threshold=TURN_STARTED_TALKING_THRESHOLD,
            speech_threshold=TURN_SPEECH_THRESHOLD,
        ),
        expected_layout="mono",
        input_sample_rate=SAMPLE_RATE,
        output_sample_rate=SAMPLE_RATE,
    )

    class SessionStream(Stream):
        def clean_up(self, webrtc_id: str):
            histories.remove(webrtc_id)
            return super().clean_up(webrtc_id)

    stream = SessionStream(
        handler=reply_handler,
        modality="audio",
        mode="send-receive",
        rtc_configuration=get_turn_configuration,
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
        token, expires_at = tokens.create()
        response.headers["Cache-Control"] = "no-store"
        return ClientSecretOutput(
            value=token,
            expires_at=expires_at,
            session=request.session or RealtimeSession(),
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
        body = Body(sdp=sdp, type="offer", webrtc_id=uuid.uuid4().hex)
        try:
            answer = await stream.offer(body)
        except Exception as error:
            logger.exception("WebRTC offer negotiation failed")
            raise HTTPException(
                status_code=502,
                detail="WebRTC offer negotiation failed",
            ) from error
        if not isinstance(answer, dict) or not isinstance(answer.get("sdp"), str):
            raise HTTPException(status_code=502, detail="WebRTC negotiation returned an invalid answer")
        return Response(content=answer["sdp"], media_type="application/sdp")

    return app
