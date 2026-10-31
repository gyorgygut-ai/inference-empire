from __future__ import annotations

import hmac
import io
import json
import logging
import os
import secrets
import time
import uuid
from typing import Any, Protocol

import numpy as np
import soundfile as sf
from dist.contract_voice import ClientSecretInput, ClientSecretOutput, RealtimeSession
from fastapi import FastAPI, HTTPException, Request, Response

from shared.inference_client import InferenceClient


class InferencePipeline(Protocol):
    def transcribe(self, audio: bytes, filename: str) -> str: ...

    def complete(self, transcript: str) -> str: ...

    def speak(self, text: str) -> tuple[bytes, int | None]: ...

logger = logging.getLogger(__name__)
SAMPLE_RATE = 24_000
TOKEN_TTL_SECONDS = 60
VAD_SPEECH_RMS_THRESHOLD = 0.01



class SessionTokens:
    def __init__(self, ttl_seconds: int = TOKEN_TTL_SECONDS):
        self.ttl_seconds = ttl_seconds
        self._tokens: dict[str, float] = {}

    def create(self) -> tuple[str, int]:
        now = int(time.time())
        token = secrets.token_urlsafe(32)
        self._tokens[token] = float(now + self.ttl_seconds)
        return token, now + self.ttl_seconds

    def validate(self, token: str) -> bool:
        expires_at = self._tokens.get(token)
        if expires_at is None:
            return False
        if expires_at <= time.time():
            del self._tokens[token]
            return False
        return True


class EnergyPauseDetector:
    def __init__(self) -> None:
        self.calls = 0
        self.speech_chunks = 0

    def vad(self, audio: tuple[int, np.ndarray], options: object) -> tuple[float, list]:
        del options
        self.calls += 1
        sample_rate, samples = audio
        values = np.asarray(samples, dtype=np.float32).reshape(-1)
        if values.size == 0:
            return 0.0, []
        if np.max(np.abs(values)) > 1.0:
            values = values / 32768.0
        rms = float(np.sqrt(np.mean(np.square(values))))
        if rms >= VAD_SPEECH_RMS_THRESHOLD:
            self.speech_chunks += 1
            return len(values) / sample_rate, []
        return 0.0, []

    def warmup(self) -> None:
        return None


def _resample(audio: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    values = np.asarray(audio, dtype=np.float32).reshape(-1)
    if source_rate == target_rate or values.size == 0:
        return values
    count = round(len(values) * target_rate / source_rate)
    return np.interp(
        np.linspace(0, max(len(values) - 1, 0), count), np.arange(len(values)), values
    ).astype(np.float32)


def _wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
    buffer = io.BytesIO()
    sf.write(buffer, audio, sample_rate, format="WAV", subtype="PCM_16")
    return buffer.getvalue()


def run_turn(
    audio: np.ndarray,
    sample_rate: int,
    client: InferencePipeline,
) -> tuple[str, str, np.ndarray]:
    samples = np.asarray(audio, dtype=np.float32).reshape(-1)
    if samples.size == 0 or not np.isfinite(samples).all() or float(np.max(np.abs(samples))) < 0.005:
        raise ValueError("speech input is empty or silent")
    normalized = samples / 32768.0 if np.max(np.abs(samples)) > 1.0 else samples
    wav = _wav_bytes(normalized, sample_rate)
    transcript = client.transcribe(wav, "audio.wav")
    if not transcript.strip():
        raise ValueError("Audio Transcriptions returned an empty transcript")
    reply = client.complete(transcript)
    if not reply.strip():
        raise ValueError("Chat Completions returned an empty response")
    response_audio, output_rate = client.speak(reply)
    decoded, decoded_rate = sf.read(
        io.BytesIO(response_audio), dtype="float32", always_2d=False
    )
    if decoded.size == 0 or not np.isfinite(decoded).all():
        raise ValueError("Audio Speech returned invalid audio")
    mono = np.asarray(decoded, dtype=np.float32)
    if mono.ndim > 1:
        mono = mono.mean(axis=1)
    if float(np.max(np.abs(mono))) < 0.001:
        raise ValueError("Audio Speech returned silent audio")
    rate = output_rate or decoded_rate
    return transcript, reply, _resample(mono, int(rate), SAMPLE_RATE)


def build_app(
    inference_client: InferencePipeline | None = None,
    token_store: SessionTokens | None = None,
    client_secret_auth_token: str | None = None,
    turn_credentials_provider: Any | None = None,
) -> FastAPI:
    from fastrtc import Stream, get_cloudflare_turn_credentials_async
    from fastrtc.stream import Body

    client = inference_client or InferenceClient.from_env()
    tokens = token_store or SessionTokens()
    trusted_server_token = client_secret_auth_token or os.environ.get(
        "SECRET_VOICE_WORKER_AUTH_TOKEN"
    )
    huggingface_token = os.environ.get("SECRET_HUGGINGFACE_TOKEN")
    if turn_credentials_provider is None and not huggingface_token:
        raise RuntimeError("SECRET_HUGGINGFACE_TOKEN is required for TURN credentials")

    async def get_turn_configuration() -> dict[str, Any]:
        if turn_credentials_provider is None:
            configuration = await get_cloudflare_turn_credentials_async(
                hf_token=huggingface_token,
                ttl=600,
            )
        else:
            configuration = await turn_credentials_provider()
        if not isinstance(configuration, dict):
            raise RuntimeError("FastRTC returned an invalid TURN configuration")
        ice_servers = configuration.get("iceServers")
        if not isinstance(ice_servers, list):
            raise RuntimeError("FastRTC returned no TURN relay")
        for server in ice_servers:
            if not isinstance(server, dict):
                continue
            urls = server.get("urls")
            urls = [urls] if isinstance(urls, str) else urls
            if (
                isinstance(urls, list)
                and any(
                    isinstance(url, str) and url.startswith(("turn:", "turns:"))
                    for url in urls
                )
                and isinstance(server.get("username"), str)
                and server["username"]
                and isinstance(server.get("credential"), str)
                and server["credential"]
            ):
                break
        else:
            raise RuntimeError("FastRTC returned no TURN relay")
        return configuration

    app = FastAPI(title="worker-voice")
    pause_detector = EnergyPauseDetector()
    app.state.pause_detector = pause_detector

    # Per-conversation state keyed by webrtc_id
    conversation_histories: dict[str, list[dict[str, str]]] = {}

    stream = Stream(
        handler=None,  # will be set below; FastRTC requires handler
        modality="audio",
        mode="send-receive",
        rtc_configuration=get_turn_configuration,
        server_rtc_configuration={
            "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
        },
    )

    async def on_turn(audio: tuple[int, np.ndarray]):
        rate, samples = audio
        transcript, reply, response_audio = run_turn(
            np.asarray(samples), rate, client
        )
        logger.info(
            "realtime turn completed transcript_chars=%d response_chars=%d",
            len(transcript),
            len(reply),
        )
        # Update conversation history
        webrtc_id = getattr(app.state, "webrtc_id", None) or "unknown"
        if webrtc_id not in conversation_histories:
            conversation_histories[webrtc_id] = [
                {
                    "role": "system",
                    "content": "You are a concise, helpful voice assistant.",
                }
            ]
        conversation_histories[webrtc_id].append({"role": "user", "content": transcript})
        conversation_histories[webrtc_id].append({"role": "assistant", "content": reply})
        max_history = 20
        if len(conversation_histories[webrtc_id]) > max_history:
            conversation_histories[webrtc_id] = conversation_histories[webrtc_id][-max_history:]
        yield SAMPLE_RATE, response_audio

    stream.handler = on_turn

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
            if not isinstance(rtc_configuration, dict):
                raise RuntimeError("FastRTC returned no RTC configuration")
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
        session_value = form.get("session")
        try:
            RealtimeSession.model_validate(
                json.loads(session_value) if isinstance(session_value, str) else {}
            )
        except (ValueError, TypeError) as error:
            raise HTTPException(status_code=422, detail="Invalid realtime session") from error
        body = Body(sdp=sdp, type="offer", webrtc_id=uuid.uuid4().hex)
        try:
            answer = await stream.offer(body)
        except Exception as error:
            logger.exception("WebRTC offer negotiation failed")
            raise HTTPException(status_code=502, detail="WebRTC offer negotiation failed") from error
        if not isinstance(answer, dict) or not isinstance(answer.get("sdp"), str):
            raise HTTPException(status_code=502, detail="WebRTC negotiation returned an invalid answer")
        return Response(content=answer["sdp"], media_type="application/sdp")

    return app

