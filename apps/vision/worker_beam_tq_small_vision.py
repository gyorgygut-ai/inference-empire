from __future__ import annotations

import threading

from beam import Image, QueueDepthAutoscaler, Volume, task_queue

from apps.vision._shared_small_vision import (
    IMAGE_PIP_DEPS,
    SmallVisionInput,
    do_inference,
    load_dependencies,
    resolve_analyze_prompt,
)

CACHE_PATH = "./hf-cache"

_INFERENCE_LOCK = threading.Lock()

image = (
    Image(python_version="python3.11")
    .add_python_packages(list(IMAGE_PIP_DEPS))
    .with_envs(
        {
            "HF_HOME": CACHE_PATH,
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
        }
    )
)


def load_deps():
    return load_dependencies(cache_dir=CACHE_PATH)


def generate(model, processor, analyze_prompt, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract."""
    req = SmallVisionInput(**kwargs)
    try:
        with _INFERENCE_LOCK:
            result = do_inference(model, processor, resolve_analyze_prompt(analyze_prompt, req.prompt), req)
            return result.model_dump()
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


@task_queue(
    name="small-vision-worker",
    cpu=4,
    memory="32Gi",
    gpu="RTX4090",
    image=image,
    on_start=load_deps,
    volumes=[Volume(name="hf-cache", mount_path=CACHE_PATH)],
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=1800,
    checkpoint_enabled=True,
    timeout=300,
    secrets=["HF_TOKEN"],
)
def dispatch(context, **kwargs) -> dict:
    model, processor, analyze_prompt = context.on_start_value
    return generate(model, processor, analyze_prompt, **kwargs)
