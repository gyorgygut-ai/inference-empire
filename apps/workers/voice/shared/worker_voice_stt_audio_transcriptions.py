from __future__ import annotations

import base64
import binascii
import logging
import os
import tempfile
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from dist.contract_voice_stt_audio_transcriptions import Input, Output
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile

from shared.auth import require_bearer_token

if TYPE_CHECKING:
    from collections.abc import Callable

MODELS = {
    "faster_whisper_large_v3": {
        "url": "https://huggingface.co/Systran/faster-whisper-large-v3",
        "path": "./hf-cache/faster_whisper_large_v3",
    },
}
MODEL_LOCK = threading.RLock()
MODEL_STATE: Any | None = None
logger = logging.getLogger(__name__)


def decode_audio(request: Input) -> bytes:
    try:
        audio = base64.b64decode(request.file_base64, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("Audio file must be valid base64") from error
    if not audio:
        raise ValueError("Audio file is empty")
    return audio


def transcription_output(text: str) -> Output:
    transcript = text.strip()
    if not transcript:
        raise ValueError("Transcription returned an empty transcript")
    return Output(text=transcript)


def load_model() -> Any:
    global MODEL_STATE

    with MODEL_LOCK:
        if MODEL_STATE is not None:
            return MODEL_STATE
        from faster_whisper import WhisperModel
        from huggingface_hub import snapshot_download

        model_path = Path(
            snapshot_download(
                repo_id=urlparse(MODELS["faster_whisper_large_v3"]["url"]).path.strip("/"),
                cache_dir=MODELS["faster_whisper_large_v3"]["path"],
                token=os.environ["SECRET_HUGGINGFACE_TOKEN"],
            )
        )
        MODEL_STATE = WhisperModel(
            str(model_path),
            device="cuda",
            compute_type="float16",
        )
        return MODEL_STATE


def transcribe(request: Input, model: Any | None = None) -> Output:
    audio = decode_audio(request)
    engine = model if model is not None else load_model()
    suffix = Path(request.filename or "audio.wav").suffix or ".audio"
    with tempfile.NamedTemporaryFile(suffix=suffix) as audio_file:
        audio_file.write(audio)
        audio_file.flush()
        segments, _ = engine.transcribe(
            audio_file.name,
            language=request.language,
            initial_prompt=request.prompt or None,
            temperature=request.temperature,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
    return transcription_output(text)


def build_app(
    transcriber: Callable[[Input], Output] = transcribe,
    api_key: str | None = None,
) -> FastAPI:
    app = FastAPI(title="workers-voice-stt-audio-transcriptions")
    expected_api_key = (
        api_key
        if api_key is not None
        else os.environ.get("GENERATED_STT_AUDIO_TRANSCRIPTIONS_API_KEY")
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/audio/transcriptions", response_model=Output)
    async def audio_transcriptions(
        http_request: Request,
        file: UploadFile = File(...),
        model: str = Form(...),
        language: str = Form("en"),
        prompt: str = Form(""),
        temperature: float = Form(0.0),
        response_format: str = Form("json"),
    ) -> Output:
        require_bearer_token(http_request, expected_api_key)
        try:
            if response_format != "json":
                raise ValueError("Only json response_format is supported")
            payload = await file.read()
            request = Input(
                model=model,
                file_base64=base64.b64encode(payload).decode("ascii"),
                filename=file.filename or "audio.wav",
                language=language,
                prompt=prompt,
                temperature=temperature,
                response_format=response_format,
            )
            return transcriber(request)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except Exception as error:
            logger.exception("Audio Transcriptions failed")
            raise HTTPException(
                status_code=500,
                detail="Audio Transcriptions failed",
            ) from error
        finally:
            await file.close()

    return app
