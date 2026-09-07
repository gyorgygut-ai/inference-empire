from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from beam import Image, QueueDepthAutoscaler, Volume, task_queue

from workers.h3._shared_minimax_h3_ref2va import (
    ValidatedRef2VAInput,
    apply_torch_shims,
    do_inference,
    load_dependencies,
)

if TYPE_CHECKING:
    from workers.services.storage.storage import Storage


CACHE_PATH = "./hf-cache"

_INFERENCE_LOCK = threading.Lock()

image = (
    Image(python_version="python3.11")
    .add_python_packages([
        "torch==2.9.1",
        "torchcodec==0.9.0",
        "diffsynth[audio]==2.1.6",
        "diffusers==0.40.0",
        "transformers==5.16.1",
        "accelerate==1.14.0",
        "bitsandbytes==0.50.2",
        "pillow==12.3.0",
        "imageio==2.37.2",
        "imageio-ffmpeg==0.6.0",
        "torchaudio==2.9.1",
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
    apply_torch_shims()
    return load_dependencies(cache_dir=CACHE_PATH)


def generate(storage: Storage, pipe, write_video_audio, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract."""
    req = ValidatedRef2VAInput(**kwargs)
    try:
        with _INFERENCE_LOCK:
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
    checkpoint_enabled=True,
    timeout=3600,
    secrets=["HF_TOKEN", "R2_ACCESS_KEY", "R2_SECRET_KEY", "R2_ENDPOINT"],
    env={
        "R2_BUCKET": "generated-media",
        "R2_ENDPOINT": "https://29b2f092b2dbc0b63f48f491ddc177ee.r2.cloudflarestorage.com",
    },
)
def dispatch(context, **kwargs) -> dict:
    storage, pipe, write_video_audio = context.on_start_value
    return generate(storage, pipe, write_video_audio, **kwargs)
