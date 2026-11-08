import base64
import io
import math
import os
import wave

import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse

SAMPLE_RATE = 24_000


def _pcm() -> bytes:
    t = np.arange(SAMPLE_RATE, dtype=np.float64) / SAMPLE_RATE
    return (np.sin(2 * math.pi * 440 * t) * 8_000).astype("<i2").tobytes()


def _wav(pcm: bytes) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(SAMPLE_RATE)
        audio.writeframes(pcm)
    return buffer.getvalue()


def build_app() -> FastAPI:
    app = FastAPI(title="worker-tts-local-stub")
    expected_token = os.environ.get("TTS_AUDIO_SPEECH_API_KEY", "")
    request_count = 0

    def authorize(request: Request) -> None:
        scheme, _, supplied = request.headers.get("authorization", "").partition(" ")
        if scheme.casefold() != "bearer" or not expected_token or supplied != expected_token:
            raise HTTPException(status_code=401, detail="Invalid API key")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/__test__/metrics")
    def metrics() -> dict[str, int]:
        return {"requests": request_count}

    @app.post("/__test__/reset")
    def reset_metrics() -> dict[str, int]:
        nonlocal request_count
        request_count = 0
        return {"requests": request_count}

    @app.post("/v1/audio/speech")
    async def speech(request: Request) -> dict[str, object]:
        nonlocal request_count
        authorize(request)
        body = await request.json()
        if not isinstance(body, dict) or not isinstance(body.get("input"), str) or not body["input"].strip():
            raise HTTPException(status_code=422, detail="input is required")
        if body.get("response_format", "wav") != "wav":
            raise HTTPException(status_code=422, detail="Only wav response_format is supported")
        request_count += 1
        return {
            "audio_base64": base64.b64encode(_wav(_pcm())).decode("ascii"),
            "format": "wav",
            "sample_rate": SAMPLE_RATE,
        }

    @app.post("/v1/audio/speech/stream")
    async def speech_stream(request: Request) -> StreamingResponse:
        nonlocal request_count
        authorize(request)
        body = await request.json()
        if not isinstance(body, dict) or not isinstance(body.get("input"), str) or not body["input"].strip():
            raise HTTPException(status_code=422, detail="input is required")
        request_count += 1
        return StreamingResponse(
            iter((_pcm(),)),
            media_type="application/octet-stream",
            headers={"X-Sample-Rate": str(SAMPLE_RATE)},
        )

    return app
