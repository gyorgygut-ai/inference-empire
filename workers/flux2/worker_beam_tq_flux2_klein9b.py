from __future__ import annotations

from typing import TYPE_CHECKING

from beam import Image, QueueDepthAutoscaler, Volume, task_queue

from workers.flux2._shared_flux2_klein9b import (
    Flux2Klein9bInput,
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
            "transformers==5.16.1",
            "accelerate==1.14.0",
            "diffusers==0.40.0",
            "sdnq==0.2.6",
            "pillow==12.3.0",
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


def generate(storage: Storage, pipe, torch_module, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract."""
    req = Flux2Klein9bInput(**kwargs)
    try:
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
    timeout=3600,
    secrets=["HF_TOKEN", "R2_ACCESS_KEY", "R2_SECRET_KEY", "R2_ENDPOINT"],
)
def dispatch(context, **kwargs) -> dict:
    storage = require_storage(None)
    return generate(storage, *context.on_start_value, **kwargs)
