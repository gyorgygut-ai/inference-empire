from __future__ import annotations

from functools import partial

from beam import Image, QueueDepthAutoscaler, task_queue

from shared.worker_realtime_voice import (
    IMAGE_PIP_DEPS,
    RealtimeVoiceInput,
    do_inference,
    load_dependencies as shared_load_dependencies,
)
from packages.shared_gpu.guard import run_guarded
from packages.shared_gpu.platform import BEAM_CACHE_PATH, beam_env

CACHE_PATH = BEAM_CACHE_PATH

image = (
    Image(
        base_image="nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04",
        python_version="python3.10",
    )
    .add_python_packages(list(IMAGE_PIP_DEPS))
    .with_envs(beam_env())
)


def load_deps():
    return shared_load_dependencies(
        f"{CACHE_PATH}/whisper",
        f"{CACHE_PATH}/qwen",
        f"{CACHE_PATH}/reference_voices"
    )


def generate(models, **kwargs) -> dict:
    return run_guarded(
        RealtimeVoiceInput,
        kwargs,
        partial(do_inference, models),
    )


@task_queue(
    name="realtime-voice-worker",
    cpu=4,
    memory="32Gi",
    gpu="RTX4090",
    image=image,
    on_start=load_deps,
    volumes=[],
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=1800,
    checkpoint_enabled=True,
    timeout=300,
    secrets=["HF_TOKEN", "R2_ACCESS_KEY", "R2_SECRET_KEY", "R2_ENDPOINT"],
)
def dispatch(context, **kwargs) -> dict:
    models = context.on_start_value
    return generate(models, **kwargs)
