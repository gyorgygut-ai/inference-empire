from __future__ import annotations

from typing import TYPE_CHECKING

from beam import Image, QueueDepthAutoscaler, Volume, task_queue

from workers.h3._shared_minimax_h3_ref2va import (
    ValidatedRef2VAInput,
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
    .add_python_packages([
        "torch==2.9.1",
        "torchcodec==0.9.0",
        "diffsynth[audio]",
        "diffusers==0.40.0",
        "transformers>=5.0,<6",
        "accelerate==1.14.0",
        "bitsandbytes",
        "pillow",
        "imageio==2.37.2",
        "imageio-ffmpeg==0.6.0",
        "torchaudio",
        "boto3==1.43.83",
    ])
    .with_envs({
        "HF_HOME": CACHE_PATH,
        "DIFFSYNTH_DOWNLOAD_SOURCE": "huggingface",
        "DIFFSYNTH_MODEL_BASE_PATH": f"{CACHE_PATH}/diffsynth",
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
    })
)


def load_deps():
    return load_dependencies(cache_dir=CACHE_PATH)


def generate(storage: Storage, pipe, write_video_audio, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract."""
    req = ValidatedRef2VAInput(**kwargs)
    try:
        return do_inference(pipe, write_video_audio, storage, req).model_dump()
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


@task_queue(
    name="minimax-h3-ref2va-worker",
    cpu=1,
    memory="32Gi",
    gpu="RTX4090",
    image=image,
    on_start=load_deps,
    volumes=[Volume(name="hf-cache", mount_path=CACHE_PATH)],
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=1800,
    timeout=3600,
    secrets=["HF_TOKEN", "R2_ACCESS_KEY", "R2_SECRET_KEY"],
    env={
        "R2_BUCKET": "generated-media",
        "R2_ENDPOINT": "https://29b2f092b2dbc0b63f48f491ddc177ee.r2.cloudflarestorage.com",
    },
)
def dispatch(context, storage: Storage, **kwargs) -> dict:
    storage = require_storage(storage)
    return generate(storage, *context.on_start_value, **kwargs)
