from __future__ import annotations

from beam import Image, QueueDepthAutoscaler, task_queue
from shared.contract_vision import SmallVisionInput
from shared.platform import BEAM_CACHE_PATH, beam_env, beam_volume
from shared.worker_vision import (
    DEPENDENCIES,
    do_inference,
    load_dependencies,
    resolve_analyze_prompt,
)

CACHE_PATH = BEAM_CACHE_PATH

image = Image(python_version="python3.11").add_python_packages(DEPENDENCIES).with_envs(beam_env())

@task_queue(
    name="workers-vision",
    cpu=4,
    memory="32Gi",
    gpu="RTX4090",
    image=image,
    on_start=lambda: load_dependencies(cache_dir=CACHE_PATH),
    volumes=[beam_volume(CACHE_PATH)],
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=0,
    checkpoint_enabled=True,
    timeout=300,
    secrets=["HF_TOKEN"],
)
def generate(context, **kwargs) -> dict:
    model, processor, analyze_prompt = context.on_start_value
    req = SmallVisionInput(**kwargs)
    prompt = resolve_analyze_prompt(analyze_prompt, req.prompt if hasattr(req, "prompt") else None)
    return do_inference(model, processor, prompt, req).model_dump()
