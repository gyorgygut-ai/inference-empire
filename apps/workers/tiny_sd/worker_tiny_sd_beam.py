from __future__ import annotations

import os

from beam import Image, QueueDepthAutoscaler, task_queue
from dist.contract_tiny_sd import Input as TinySDInput
from shared.platform import beam_env
from shared.worker_tiny_sd import (
    DEPENDENCIES,
    MODEL_CACHES,
    do_inference,
    load_dependencies,
    load_pipeline_lazy,
    model_volumes,
)

CACHE_PATH = MODEL_CACHES["segmind_tiny_sd"]["path"]
VOLUMES = model_volumes()

image = Image(python_version="python3.11").add_python_packages(
    DEPENDENCIES
).with_envs(
    beam_env(
        cache_path=CACHE_PATH,
        extra={
            "SECRET_HUGGINGFACE_TOKEN": os.environ["SECRET_HUGGINGFACE_TOKEN"],
            "SECRET_R2_ACCESS_KEY": os.environ["SECRET_R2_ACCESS_KEY"],
            "SECRET_R2_SECRET_KEY": os.environ["SECRET_R2_SECRET_KEY"],
            "SECRET_R2_ENDPOINT": os.environ["SECRET_R2_ENDPOINT"],
            "SECRET_R2_BUCKET": os.environ["SECRET_R2_BUCKET"],
        },
    )
)

@task_queue(
    name="worker-tiny_sd",
    cpu=4,
    memory="32Gi",
    gpu="RTX4090",
    image=image,
    on_start=load_dependencies,
    volumes=VOLUMES,
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=0,
    checkpoint_enabled=True,
    timeout=300,
    secrets=[],
)
def generate(context, **kwargs) -> dict:
    storage, pipe, torch_module = context.on_start_value
    if pipe is None:
        # Lazy load model on first request (not at container startup)
        pipe, torch_module = load_pipeline_lazy()
    req = TinySDInput(**kwargs)
    return do_inference(pipe, torch_module, storage, req).model_dump()
