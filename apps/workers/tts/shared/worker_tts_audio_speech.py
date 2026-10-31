from __future__ import annotations

import base64
import importlib
import io
import logging
import os
import threading
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import numpy as np
import soundfile as sf
from dist.contract_tts_audio_speech import Input, Output
from fastapi import FastAPI, HTTPException, Request, Response

from shared.auth import require_bearer_token

if TYPE_CHECKING:
    from collections.abc import Callable

MODELS = {
    "resembleai_chatterbox_tts": {
        "url": "https://huggingface.co/ResembleAI/chatterbox",
        "path": "./hf-cache/resembleai_chatterbox_tts",
    },
}
MODEL_LOCK = threading.RLock()
MODEL_STATE: Any | None = None
SAMPLE_RATE = 24_000
logger = logging.getLogger(__name__)


def encode_audio(audio: np.ndarray, sample_rate: int) -> Output:
    samples = np.asarray(audio, dtype=np.float32).reshape(-1)
    if samples.size == 0 or not np.isfinite(samples).all():
        raise ValueError("TTS returned invalid audio")
    if float(np.max(np.abs(samples))) < 0.001:
        raise ValueError("TTS returned silent audio")
    buffer = io.BytesIO()
    sf.write(buffer, samples, sample_rate, format="WAV", subtype="PCM_16")
    return Output(
        audio_base64=base64.b64encode(buffer.getvalue()).decode("ascii"),
        format="wav",
        sample_rate=sample_rate,
    )


def load_model() -> Any:
    global MODEL_STATE
    with MODEL_LOCK:
        if MODEL_STATE is not None:
            return MODEL_STATE
        hub_constants = importlib.import_module("huggingface_hub.constants")
        hub_auth = importlib.import_module("huggingface_hub")
        previous_cache = hub_constants.HF_HUB_CACHE
        hub_constants.HF_HUB_CACHE = MODELS["resembleai_chatterbox_tts"]["path"]
        try:
            hub_auth.login(token=os.environ["SECRET_HUGGINGFACE_TOKEN"], add_to_git_credential=False)
            perth = importlib.import_module("perth")
            if getattr(perth, "PerthImplicitWatermarker", None) is None:
                setattr(perth, "PerthImplicitWatermarker", perth.DummyWatermarker)
            chatterbox = importlib.import_module("chatterbox.tts")
            repo_id = urlparse(MODELS["resembleai_chatterbox_tts"]["url"]).path.strip("/")
            if chatterbox.REPO_ID != repo_id:
                raise RuntimeError("Chatterbox package repo differs from the declared model")
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            MODEL_STATE = chatterbox.ChatterboxTTS.from_pretrained(device=device)
        finally:
            hub_constants.HF_HUB_CACHE = previous_cache
        return MODEL_STATE


def synthesize(request: Input, model: Any | None = None) -> Output:
    if request.response_format not in (None, "wav"):
        raise ValueError("Only wav response_format is supported")
    engine = model if model is not None else load_model()
    with MODEL_LOCK:
        generated = engine.generate(request.input)
    audio = np.asarray(generated.squeeze().detach().cpu(), dtype=np.float32).reshape(-1)
    speed = float(request.speed) if request.speed is not None else 1.0
    if speed != 1.0 and audio.size:
        output_size = max(1, round(audio.size / speed))
        audio = np.interp(np.linspace(0, audio.size - 1, output_size), np.arange(audio.size), audio).astype(np.float32)
    rate = int(getattr(engine, "sr", SAMPLE_RATE))
    return encode_audio(audio, rate)


def build_app(generator: Callable[[Input], Output] = synthesize, api_key: str | None = None) -> FastAPI:
    app = FastAPI(title="worker-tts")
    expected_api_key = api_key if api_key is not None else os.environ.get("SECRET_TTS_AUDIO_SPEECH_API_KEY")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/audio/speech")
    def audio_speech(request: Input, http_request: Request) -> Response:
        require_bearer_token(http_request, expected_api_key)
        if request.response_format not in (None, "wav"):
            raise HTTPException(status_code=422, detail="Only wav response_format is supported")
        try:
            result = generator(request)
            if result.format != "wav":
                raise ValueError("TTS returned an unsupported audio format")
            audio = base64.b64decode(result.audio_base64, validate=True)
            with sf.SoundFile(io.BytesIO(audio)) as stream:
                samples = stream.read(dtype="float32")
                if stream.format != "WAV" or stream.samplerate != result.sample_rate:
                    raise ValueError("TTS returned invalid WAV metadata")
                if samples.size == 0 or not np.isfinite(samples).all() or float(np.max(np.abs(samples))) < 0.001:
                    raise ValueError("TTS returned empty or silent audio")
        except ValueError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
        except Exception as error:
            logger.exception("Audio Speech generation failed")
            raise HTTPException(status_code=500, detail="Audio Speech generation failed") from error
        return Response(content=audio, media_type="audio/wav")

    return app
