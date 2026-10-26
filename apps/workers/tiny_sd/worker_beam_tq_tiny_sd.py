from __future__ import annotations

from functools import partial

from beam import Image, QueueDepthAutoscaler, task_queue

from shared.worker_tiny_sd import (
    IMAGE_PIP_DEPS,
    TinySDInput,
    do_inference,
    load_dependencies,
)
from packages.shared_gpu.guard import run_guarded
from packages.shared_gpu.platform import BEAM_CACHE_PATH, beam_env, beam_volume

CACHE_PATH = BEAM_CACHE_PATH

image = (
    Image(python_version="python3.11")
    .add_python_packages(list(IMAGE_PIP_DEPS))
    .with_envs(beam_env())
)


def generate(storage, pipe, torch_module, **kwargs) -> dict:
    return run_guarded(
        TinySDInput, kwargs, partial(do_inference, pipe, torch_module, storage)
    )


@task_queue(
    name="workers-tiny_sd",
    cpu=4,
    memory="32Gi",
    gpu="RTX4090",
    image=image,
    on_start=load_dependencies,
    volumes=[beam_volume(CACHE_PATH)],
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=1800,
    checkpoint_enabled=True,
    timeout=300,
    secrets=["HF_TOKEN", "R2_ACCESS_KEY", "R2_SECRET_KEY", "R2_ENDPOINT"],
)
def dispatch(context, **kwargs) -> dict:
    storage, pipe, torch_module = context.on_start_value
    return generate(storage, pipe, torch_module, **kwargs)
