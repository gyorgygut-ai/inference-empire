from __future__ import annotations

from functools import partial

from beam import Image, QueueDepthAutoscaler, Volume, asgi

from apps.realtime_voice.shared.worker_realtime_voice import (
    CHATTERBOX_TTS_NO_DEPS,
    IMAGE_PIP_DEPS,
    QWEN_DIR_NAME,
    REFERENCE_VOICES_DIR_NAME,
    WHISPER_DIR_NAME,
    RealtimeVoiceInput,
    build_app,
    do_inference,
)
from apps.realtime_voice.shared.worker_realtime_voice import (
    load_dependencies as shared_load_dependencies,
)
from packages.shared_gpu.guard import run_guarded

VOLUME_NAME = "models"
MOUNT_PATH = "/volumes/models"
WHISPER_PATH = f"{MOUNT_PATH}/{WHISPER_DIR_NAME}"
QWEN_PATH = f"{MOUNT_PATH}/{QWEN_DIR_NAME}"
REFERENCE_DIR = f"{MOUNT_PATH}/{REFERENCE_VOICES_DIR_NAME}"

image = (
    Image(
        base_image="nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04",
        python_version="python3.10",
    )
    .add_commands(["apt-get update && apt-get install -y ffmpeg"])
    .add_python_packages(list(IMAGE_PIP_DEPS))
    .add_commands([f"pip install --no-deps {CHATTERBOX_TTS_NO_DEPS}"])
    .with_envs({"HF_HUB_ENABLE_HF_TRANSFER": "1", "HF_HOME": "/volumes/models/.hf_cache"})
)

volume = Volume(name=VOLUME_NAME, mount_path=MOUNT_PATH)


def load_models():
    return shared_load_dependencies(WHISPER_PATH, QWEN_PATH, REFERENCE_DIR)


def load_dependencies():
    return load_models()


def generate(models: dict, **kwargs) -> dict:
    return run_guarded(RealtimeVoiceInput, kwargs, partial(do_inference, models))


@asgi(
    name="realtime-voice-qwen-worker",
    image=image,
    volumes=[volume],
    on_start=load_models,
    gpu="RTX4090",
    cpu=4,
    memory="32Gi",
    concurrent_requests=1,
    keep_warm_seconds=10,
    timeout=-1,
    authorized=True,
    checkpoint_enabled=True,
    secrets=["HF_TOKEN"],
    autoscaler=QueueDepthAutoscaler(max_containers=1, min_containers=0),
)
def worker(context):
    models = context.on_start_value
    return build_app(models)
