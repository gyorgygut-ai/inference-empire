"""Beam.cloud @asgi Chatterbox TTS worker — OpenAI-compatible audio endpoint.

Exposes the OpenAI TTS surface that OpenWebUI (and other clients) speak:

* ``GET  /v1/audio/voices``  (and ``/audio/voices``)  -> ``{"voices":[{id,name}]}``
* ``POST /v1/audio/speech``  (and ``/audio/speech``)  -> WAV audio bytes
  body: ``{"model", "input", "voice", "response_format?"}``

The chosen ``voice`` is cloned zero-shot from ``voices/reference_voices/<voice>.wav``.
GPU-only (RTX4090); English-only model.
"""

from __future__ import annotations

import asyncio
import io
import time
import wave

from beam import Image, QueueDepthAutoscaler, asgi
from fastapi import FastAPI, Request
from fastapi.responses import Response

from handlers.chatterbox_tts import TARGET_SR, Chatterbox

image = (
    Image(python_version="python3.11")
    .add_python_packages(
        [
            "fastapi",
            "uvicorn[standard]",
            "numpy",
            "soundfile",
            "chatterbox-tts",
            "librosa>=0.10",
        ]
    )
)


def load_model():
    t0 = time.time()
    tts = Chatterbox(device="cuda").load()
    print(f"[INIT] Chatterbox ready in {time.time() - t0:.1f}s")
    return tts


def _pcm_to_wav(pcm16: bytes, sr: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm16)
    return buf.getvalue()


@asgi(
    name="voice-chatterbox",
    image=image,
    on_start=load_model,
    gpu="RTX4090",
    cpu=4,
    memory="32Gi",
    concurrent_requests=4,
    keep_warm_seconds=10,
    timeout=-1,
    authorized=True,
    secrets=["HF_TOKEN"],
    autoscaler=QueueDepthAutoscaler(max_containers=1, min_containers=0),
)
def worker(context):
    tts = context.on_start_value
    app = FastAPI()

    def _list():
        return {"voices": [{"id": v, "name": v} for v in tts.voices()]}

    async def _speak(body: dict) -> Response:
        text = body.get("input") or body.get("text") or ""
        voice = body.get("voice") or "GutAI"
        pcm = await asyncio.to_thread(tts.generate, text, voice)
        return Response(content=_pcm_to_wav(pcm, TARGET_SR), media_type="audio/wav")

    @app.get("/v1/audio/voices")
    async def list_voices_v1():
        return _list()

    @app.get("/audio/voices")
    async def list_voices():
        return _list()

    @app.post("/v1/audio/speech")
    async def speech_v1(request: Request):
        return await _speak(await request.json())

    @app.post("/audio/speech")
    async def speech(request: Request):
        return await _speak(await request.json())

    return app
