from __future__ import annotations

from functools import partial
from pathlib import Path

import modal

from packages.realtime_voice.shared import (
    CHATTERBOX_TTS_NO_DEPS,
    IMAGE_PIP_DEPS,
    QWEN_DIR_NAME,
    REFERENCE_VOICES_DIR_NAME,
    WHISPER_DIR_NAME,
    RealtimeVoiceInput,
    build_app,
    do_inference,
)
from packages.realtime_voice.shared import (
    load_dependencies as shared_load_dependencies,
)
from packages.shared_gpu.guard import run_guarded
from packages.shared_gpu.platform import MODAL_HF_MOUNT, modal_env, modal_volume

app = modal.App("realtime-voice-qwen-worker")

dotenv_secret = modal.Secret.from_dotenv(str(Path(__file__).parent.parent.parent / ".env"))
hf_cache_vol = modal_volume()
MODEL_MOUNT = MODAL_HF_MOUNT
WHISPER_PATH = f"{MODEL_MOUNT}/{WHISPER_DIR_NAME}"
QWEN_PATH = f"{MODEL_MOUNT}/{QWEN_DIR_NAME}"
REFERENCE_DIR = f"{MODEL_MOUNT}/{REFERENCE_VOICES_DIR_NAME}"

image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04", add_python="3.10"
    )
    .apt_install("ffmpeg", "libsndfile1")
    .pip_install(*IMAGE_PIP_DEPS)
    .run_commands(f"pip install --no-deps {CHATTERBOX_TTS_NO_DEPS}")
    .env(modal_env())
    .add_local_python_source("apps", "apps")
    .add_local_python_source("packages", "packages")
)


def generate(models: dict, **kwargs) -> dict:
    return run_guarded(RealtimeVoiceInput, kwargs, partial(do_inference, models))


@app.cls(
    image=image,
    gpu="L4",
    secrets=[dotenv_secret],
    volumes={MODEL_MOUNT: hf_cache_vol},
    timeout=3600,
    memory=32768,
    scaledown_window=60,
    max_containers=1,
)
class RealtimeVoiceWorker:
    @modal.enter()
    def load(self):
        print("[INIT] loading realtime-voice-qwen models", flush=True)
        self.models = shared_load_dependencies(WHISPER_PATH, QWEN_PATH, REFERENCE_DIR)
        print("[INIT] models loaded", flush=True)

    @modal.method()
    def generate(self, **kwargs) -> dict:
        return generate(self.models, **kwargs)


@app.function(
    image=image,
    volumes={MODEL_MOUNT: hf_cache_vol},
    timeout=3600,
    scaledown_window=60,
    max_containers=1,
)
@modal.asgi_app()
def web():
    models = shared_load_dependencies(WHISPER_PATH, QWEN_PATH, REFERENCE_DIR)
    return build_app(models)


def load_dependencies() -> dict:
    """Modal entrypoint alias for test-mocking parity with Beam/Flash."""
    return shared_load_dependencies(WHISPER_PATH, QWEN_PATH, REFERENCE_DIR)
