from __future__ import annotations

import os

from beam import Image, QueueDepthAutoscaler, task_queue
from dist.contract_vision import Input as SmallVisionInput
from shared.platform import beam_env
from shared.worker_vision import (
    DEPENDENCIES,
    MODEL_CACHES,
    do_inference,
    load_dependencies,
    load_pipeline_lazy,
    model_volumes,
    resolve_analyze_prompt,
)

CACHE_PATH = MODEL_CACHES["qwen2_vl_2b_instruct"]["path"]
VOLUMES = model_volumes()

image = Image(python_version="python3.11").add_python_packages(DEPENDENCIES).with_envs(
    beam_env(
        cache_path=CACHE_PATH,
        extra={
            "SECRET_HUGGINGFACE_TOKEN": os.environ["SECRET_HUGGINGFACE_TOKEN"]
        },
    )
)

@task_queue(
    name="worker-vision",
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
    model, processor, analyze_prompt = context.on_start_value
    if model is None:
        # Lazy load model on first request (not at container startup)
        model, processor, analyze_prompt = load_pipeline_lazy()
    req = SmallVisionInput(**kwargs)
    prompt = resolve_analyze_prompt(analyze_prompt, req.prompt if hasattr(req, "prompt") else None)
    return do_inference(model, processor, prompt, req).model_dump()
