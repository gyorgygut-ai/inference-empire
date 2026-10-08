from __future__ import annotations

from beam import Image, QueueDepthAutoscaler, task_queue

from packages.shared_gpu.guard import run_guarded
from packages.shared_gpu.platform import BEAM_CACHE_PATH, beam_env, beam_volume
from packages.vision.shared import (
    IMAGE_PIP_DEPS,
    SmallVisionInput,
    do_inference,
    load_dependencies,
    resolve_analyze_prompt,
)

CACHE_PATH = BEAM_CACHE_PATH

image = (
    Image(python_version="python3.11")
    .add_python_packages(list(IMAGE_PIP_DEPS))
    .with_envs(beam_env())
)


def load_deps():
    return load_dependencies(cache_dir=CACHE_PATH)


def generate(model, processor, analyze_prompt, **kwargs) -> dict:
    return run_guarded(
        SmallVisionInput,
        kwargs,
        lambda req: do_inference(
            model, processor, resolve_analyze_prompt(analyze_prompt, req.prompt), req
        ),
    )


@task_queue(
    name="small-vision-worker",
    cpu=4,
    memory="32Gi",
    gpu="RTX4090",
    image=image,
    on_start=load_deps,
    volumes=[beam_volume(CACHE_PATH)],
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=1800,
    checkpoint_enabled=True,
    timeout=300,
    secrets=["HF_TOKEN"],
)
def dispatch(context, **kwargs) -> dict:
    model, processor, analyze_prompt = context.on_start_value
    return generate(model, processor, analyze_prompt, **kwargs)
