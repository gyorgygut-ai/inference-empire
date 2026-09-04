from __future__ import annotations

from typing import TYPE_CHECKING

from beam import Image, QueueDepthAutoscaler, Volume, endpoint

from workers.services.storage.real_r2 import require_storage
from workers.vision._shared_small_vision import (
    SmallVisionInput,
    SmallVisionOutput,
    load_dependencies,
    run_analyze,
)

if TYPE_CHECKING:
    from workers.services.storage.storage import Storage

CACHE_PATH = "./hf-cache"

image = (
    Image(python_version="python3.11")
    .add_python_packages(
        [
            "torch==2.9.1",
            "transformers>=4.57,<5",
            "torchvision",
            "pillow",
            "accelerate",
        ]
    )
    .with_envs(
        {
            "HF_HOME": CACHE_PATH,
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
        }
    )
)


def load_deps():
    return load_dependencies(cache_dir=CACHE_PATH)


@endpoint(
    name="small-vision-worker",
    cpu=2,
    memory="16Gi",
    gpu="A10G",
    image=image,
    on_start=load_deps,
    volumes=[Volume(name="hf-cache", mount_path=CACHE_PATH)],
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=0,
    checkpoint_enabled=True,
)
def analyze(context, image_base64: str, storage: Storage):
    storage = require_storage(storage)
    model, processor, analyze_prompt = context.on_start_value
    try:
        req = SmallVisionInput(image_base64=image_base64)
        result = run_analyze(model, processor, analyze_prompt, req)
        return result.model_dump() if isinstance(result, SmallVisionOutput) else result
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"inference failed: {e}")
