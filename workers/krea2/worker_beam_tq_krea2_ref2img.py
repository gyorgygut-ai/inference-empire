from __future__ import annotations

from typing import TYPE_CHECKING

from beam import Image, QueueDepthAutoscaler, Volume, task_queue

from workers.krea2._shared_krea2_ref2img import (
    Krea2Ref2ImgInput,
    do_inference,
    ensure_dotenv,
    load_dependencies,
)
from workers.services.storage.r2_storage import require_storage

if TYPE_CHECKING:
    from workers.services.storage.storage import Storage


ensure_dotenv()

CACHE_PATH = "./hf-cache"

image = (
    Image(python_version="python3.11")
    .add_python_packages(
        [
            "torch==2.9.1",
            "diffusers==0.39.0",
            "transformers>=4.57,<5",
            "accelerate==1.14.0",
            "safetensors==0.8.0",
            "hf_transfer==0.1.9",
            "pillow==12.3.0",
            "protobuf==6.33.6",
            "opencv-python-headless==4.12.0.88",
            "peft==0.17.0",
            "boto3==1.43.83",
        ]
    )
    .with_envs(
        {
            "HF_HOME": CACHE_PATH,
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "R2_ENDPOINT": "https://29b2f092b2dbc0b63f48f491ddc177ee.r2.cloudflarestorage.com",
            "R2_BUCKET": "generated-media",
        }
    )
)


def load_deps():
    return load_dependencies(cache_dir=CACHE_PATH)


def generate(storage: Storage, pipe, runtime_dir, torch_module, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract."""
    req = Krea2Ref2ImgInput(**kwargs)
    try:
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
    timeout=3600,
    secrets=["HF_TOKEN", "R2_ACCESS_KEY", "R2_SECRET_KEY", "R2_ENDPOINT"],
    env={
        "PYTORCH_NVML_BASED_CUDA_CHECK": "0",
    },
)
def dispatch(context, **kwargs) -> dict:
    storage = require_storage(None)
    return generate(storage, *context.on_start_value, **kwargs)
