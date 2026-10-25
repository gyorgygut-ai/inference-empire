from __future__ import annotations

from functools import partial
from pathlib import Path

import modal

from shared.worker_realtime_voice import (
    RealtimeVoiceInput,
    do_inference,
    load_dependencies,
)
from packages.shared_gpu.guard import run_guarded
from packages.shared_gpu.platform import MODAL_HF_MOUNT, modal_env, modal_volume

app = modal.App("realtime-voice-qwen-worker")

dotenv_secret = modal.Secret.from_dotenv(str(Path(__file__).parent.parent.parent / ".env"))
hf_cache_vol = modal_volume()

# Check what IMAGE_PIP_DEPS contains for realtime_voice
IMAGE_PIP_DEPS = [
    "fastapi==0.141.1",
    "uvicorn[standard]==0.52.4",
    "numpy==1.26.4",
    "setuptools==84.0.0",
    "soundfile==0.14.0",
    "faster-whisper==1.2.1",
    "ctranslate2==4.4.0",
    "transformers==5.2.0",
    "torch==2.6.0",
    "torchaudio==2.6.0",
    "accelerate==1.14.0",
    "bitsandbytes==0.50.2",
    "librosa==0.11.0",
    "diffusers==0.29.0",
    "conformer==0.3.2",
    "safetensors==0.5.3",
    "pykakasi==2.3.0",
    "s3tokenizer==0.3.0",
    "resemble-perth==1.0.1",
    "spacy-pkuseg==1.0.1",
]

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "libsndfile1")
    .pip_install(*IMAGE_PIP_DEPS)
    .env(modal_env())
)


def generate(models, **kwargs) -> dict:
    return run_guarded(
        RealtimeVoiceInput,
        kwargs,
        partial(do_inference, models),
    )


@app.cls(
    image=image,
    gpu="L4",
    secrets=[dotenv_secret],
    volumes={MODAL_HF_MOUNT: hf_cache_vol},
    timeout=300,
    memory=32768,
    scaledown_window=150,
    max_containers=1,
)
class RealtimeVoiceWorker:
    @modal.enter()
    def load(self):
        self.models = load_dependencies()

    @modal.method()
    def generate(self, **kwargs) -> dict:
        return generate(self.models, **kwargs)


@app.function(image=modal.Image.debian_slim().pip_install("fastapi[standard]==0.141.1"), timeout=300)
@modal.fastapi_endpoint(method="POST")
def generate_web(item: dict) -> dict:
    return RealtimeVoiceWorker().generate.remote(**item)
