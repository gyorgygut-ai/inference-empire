from __future__ import annotations

import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

from beam import Image, QueueDepthAutoscaler, Volume, task_queue

from workers.flux2.generate_flux2_klein9b import (
    Flux2Klein9bInput,
    load_pipeline as shared_load_pipeline,
    run_generate,
)

from workers.services.storage.real_r2 import require_storage
if TYPE_CHECKING:
    from workers.services.storage.storage import Storage


START = time.time()


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(Path(__file__).parent.parent / ".env")


CACHE_PATH = "./hf-cache"

image = (
    Image(python_version="python3.11")
    .add_python_packages(
        [
            "torch==2.9.1",
            "transformers>=5.0,<6",
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


def load_pipeline():
    return shared_load_pipeline()


@task_queue(
    name="flux2-klein9b-worker",
    cpu=4,
    memory="32Gi",
    gpu="RTX4090",
    image=image,
    on_start=load_pipeline,
    volumes=[Volume(name="hf-cache", mount_path=CACHE_PATH)],
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=1800,
    checkpoint_enabled=True,
    timeout=3600,
    secrets=["HF_TOKEN", "R2_ACCESS_KEY", "R2_SECRET_KEY", "R2_ENDPOINT"],
)
def generate(context, storage: Storage, **kwargs) -> dict:
    storage = require_storage(storage)
    pipe, torch_module = context.on_start_value
    try:
        req = Flux2Klein9bInput(**kwargs)
        return run_generate(pipe, torch_module, storage, req).model_dump()
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}")
