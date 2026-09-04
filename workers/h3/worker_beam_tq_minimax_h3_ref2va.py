from __future__ import annotations

import time
from typing import TYPE_CHECKING

from beam import Image, QueueDepthAutoscaler, Volume, task_queue

from workers.h3.generate_minimax_h3_ref2va import (
    ValidatedRef2VAInput,
    load_pipeline as shared_load_pipeline,
    run_generate,
)

from workers.services.storage.real_r2 import require_storage
if TYPE_CHECKING:
    from workers.services.storage.storage import Storage

START_TIME = time.time()


CACHE_PATH = "./hf-cache"

image = (
    Image(python_version="python3.11")
    .add_python_packages([
        "torch==2.9.1",
        "torchcodec==0.9.0",
        "diffsynth[audio]",
        "transformers>=4.57,<5",
        "bitsandbytes",
        "pillow",
        "imageio[ffmpeg]",
        "torchaudio",
        "boto3",
    ])
    .with_envs({
        "HF_HOME": CACHE_PATH,
        "DIFFSYNTH_DOWNLOAD_SOURCE": "huggingface",
        "DIFFSYNTH_MODEL_BASE_PATH": f"{CACHE_PATH}/diffsynth",
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
    })
)


def load_pipeline():
    return shared_load_pipeline()


@task_queue(
    name="minimax-h3-ref2va-worker",
    cpu=1,
    memory="32Gi",
    gpu="RTX4090",
    image=image,
    on_start=load_pipeline,
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
def generate(context, storage: Storage, **kwargs) -> dict:
    storage = require_storage(storage)
    try:
        pipe, write_video_audio = context.on_start_value
        req = ValidatedRef2VAInput(**kwargs)
        return run_generate(pipe, write_video_audio, storage, req).model_dump()
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise
