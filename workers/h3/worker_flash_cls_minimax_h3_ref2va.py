from __future__ import annotations

import os
from typing import TYPE_CHECKING

from runpod_flash import Endpoint, GpuGroup

from workers.h3._shared_minimax_h3_ref2va import (
    ValidatedRef2VAInput,
    do_inference,
    load_dependencies,
)
from workers.services.storage.r2_storage import require_storage

if TYPE_CHECKING:
    from workers.services.storage.storage import Storage


def generate(storage: Storage, pipe, write_video_audio, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract."""
    req = ValidatedRef2VAInput(**kwargs)
    try:
        return do_inference(pipe, write_video_audio, storage, req).model_dump()
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


@Endpoint(
    name="minimax-h3-ref2va-worker",
    gpu=[GpuGroup.AMPERE_48],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env={
        "HF_HOME": "/runpod-volume/huggingface-cache",
        "DIFFSYNTH_DOWNLOAD_SOURCE": "huggingface",
        "DIFFSYNTH_MODEL_BASE_PATH": "/runpod-volume/huggingface-cache/diffsynth",
        "FLASH_TEMPLATE_SALT": "ref2va",
        "R2_BUCKET": os.environ.get("R2_BUCKET", "generated-media"),
        "R2_ENDPOINT": os.environ.get("R2_ENDPOINT", ""),
        "R2_ACCESS_KEY": os.environ.get("R2_ACCESS_KEY", ""),
        "R2_SECRET_KEY": os.environ.get("R2_SECRET_KEY", ""),
    },
    dependencies=[
        "torch==2.9.1",
        "diffusers==0.40.0",
        "transformers==5.16.1",
        "accelerate==1.14.0",
        "torchcodec==0.9.0",
        "diffsynth[audio]==2.1.6",
        "bitsandbytes==0.50.2",
        "pillow==12.3.0",
        "imageio==2.37.2",
        "imageio-ffmpeg==0.6.0",
        "torchaudio==2.9.1",
        "boto3==1.43.83",
    ],
)
class MiniMaxH3Ref2VAWorker:
    Input = ValidatedRef2VAInput

    def __init__(self):
        self.storage = require_storage(None)
        self.pipe, self.write_video_audio = load_dependencies()

    def generate(self, **kwargs) -> dict:
        """Validate at boundary, delegate, return output contract."""
        return generate(self.storage, self.pipe, self.write_video_audio, **kwargs)
