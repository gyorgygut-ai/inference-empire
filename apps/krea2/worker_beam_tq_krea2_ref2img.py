from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from beam import Image, QueueDepthAutoscaler, Volume, task_queue

from apps.krea2._shared_krea2_ref2img import (
    IMAGE_PIP_DEPS,
    Krea2Ref2ImgInput,
    do_inference,
    load_dependencies,
)

if TYPE_CHECKING:
    from packages.shared_gpu.artifacts.storage import Storage


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


def generate(storage: Storage, pipe, runtime_dir, torch_module, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract."""
    req = Krea2Ref2ImgInput(**kwargs)
    try:
        with _INFERENCE_LOCK:
            return do_inference(pipe, runtime_dir, torch_module, storage, req).model_dump()
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


@task_queue(
    name="krea2-ref2img-worker",
    cpu=8,
    memory="64Gi",
    gpu="RTX5090",
    image=image,
    on_start=load_deps,
    volumes=[Volume(name="hf-cache", mount_path=CACHE_PATH)],
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=1800,
    checkpoint_enabled=True,
    timeout=300,
    secrets=["HF_TOKEN", "R2_ACCESS_KEY", "R2_SECRET_KEY", "R2_ENDPOINT"],
    env={
        "PYTORCH_NVML_BASED_CUDA_CHECK": "0",
    },
)
def dispatch(context, **kwargs) -> dict:
    storage, pipe, runtime_dir, torch_module = context.on_start_value
    return generate(storage, pipe, runtime_dir, torch_module, **kwargs)
