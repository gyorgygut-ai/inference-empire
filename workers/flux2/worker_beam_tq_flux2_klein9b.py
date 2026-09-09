from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from beam import Image, QueueDepthAutoscaler, Volume, task_queue

from workers.flux2._shared_flux2_klein9b import (
    IMAGE_PIP_DEPS,
    Flux2Klein9bInput,
    do_inference,
    load_dependencies,
)

if TYPE_CHECKING:
    from workers.services.storage.storage import Storage


CACHE_PATH = "./hf-cache"

_INFERENCE_LOCK = threading.Lock()

image = (
    Image(python_version="python3.11")
    .add_python_packages(list(IMAGE_PIP_DEPS))
    .with_envs(
        {
            "HF_HOME": CACHE_PATH,
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "SDNQ_USE_TRITON_MM": "0",
        }
    )
)


def generate(storage: Storage, pipe, torch_module, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract."""
    req = Flux2Klein9bInput(**kwargs)
    try:
        with _INFERENCE_LOCK:
            return do_inference(pipe, torch_module, storage, req).model_dump()
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


@task_queue(
    name="flux2-klein9b-worker",
    cpu=4,
    memory="32Gi",
    gpu="RTX4090",
    image=image,
    on_start=load_dependencies,
    volumes=[Volume(name="hf-cache", mount_path=CACHE_PATH)],
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=1800,
    checkpoint_enabled=True,
    timeout=300,
    secrets=["HF_TOKEN", "R2_ACCESS_KEY", "R2_SECRET_KEY", "R2_ENDPOINT"],
)
def dispatch(context, **kwargs) -> dict:
    storage, pipe, torch_module = context.on_start_value
    return generate(storage, pipe, torch_module, **kwargs)
