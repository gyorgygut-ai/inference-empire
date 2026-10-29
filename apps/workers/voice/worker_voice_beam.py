"""Thin Beam ASGI wrapper for the FastRTC voice worker."""

from beam import Image, QueueDepthAutoscaler, Volume, asgi
from shared.worker_voice import (
    CHATTERBOX_TTS_NO_DEPS,
    IMAGE_PIP_DEPS,
    build_app,
    model_volumes,
)

image = (
    Image(python_version="python3.11")
    .add_commands(["apt-get update && apt-get install -y ffmpeg"])
    .add_python_packages(IMAGE_PIP_DEPS)
    .add_commands([f"pip install --no-deps {CHATTERBOX_TTS_NO_DEPS}"])
    .with_envs({"HF_HOME": "./hf-cache", "HF_HUB_ENABLE_HF_TRANSFER": "1"})
)
reference_volume = Volume(name="hf-cache", mount_path="./hf-cache")
MODEL_VOLUMES = model_volumes()


@asgi(
    name="workers-voice",
    image=image,
    volumes=[reference_volume, *MODEL_VOLUMES],
    gpu="RTX4090",
    cpu=4,
    memory="32Gi",
    concurrent_requests=1,
    keep_warm_seconds=0,
    timeout=-1,
    authorized=True,
    secrets=["HF_TOKEN"],
    autoscaler=QueueDepthAutoscaler(max_containers=1, min_containers=0),
)
def generate(context):
    del context  # Beam injects this parameter by name; the ASGI app does not use it.
    return build_app()
