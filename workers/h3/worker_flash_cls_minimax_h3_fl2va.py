from __future__ import annotations

import os
from typing import TYPE_CHECKING

from runpod_flash import Endpoint, GpuGroup

from workers.h3._shared_minimax_h3_fl2va import (
    MiniMaxH3Fl2VAInput,
    load_dependencies,
    run_generate,
)
from workers.services.storage.real_r2 import require_storage

if TYPE_CHECKING:
    from workers.services.storage.storage import Storage


@Endpoint(
    name="minimax-h3-fl2va-worker",
    gpu=[GpuGroup.AMPERE_24],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env={
        "HF_HOME": "/runpod-volume/huggingface-cache",
        "DIFFSYNTH_DOWNLOAD_SOURCE": "huggingface",
        "DIFFSYNTH_MODEL_BASE_PATH": "/runpod-volume/huggingface-cache/diffsynth",
        "FLASH_TEMPLATE_SALT": "fl2va",
        "R2_BUCKET": os.environ.get("R2_BUCKET", "generated-media"),
        "R2_ENDPOINT": os.environ.get("R2_ENDPOINT", ""),
        "R2_ACCESS_KEY": os.environ.get("R2_ACCESS_KEY", ""),
        "R2_SECRET_KEY": os.environ.get("R2_SECRET_KEY", ""),
    },
    dependencies=[
        "torch==2.9.1",
        "torchcodec==0.9.0",
        "diffsynth[audio]",
        "transformers>=4.57,<5",
        "bitsandbytes",
        "pillow",
        "imageio[ffmpeg]",
        "torchaudio",
        "boto3",
    ],
)
class MiniMaxH3Fl2VAWorker:
    Input = MiniMaxH3Fl2VAInput

    def __init__(self, storage: Storage):
        storage = require_storage(storage)
        self.storage = storage
        self.pipe, self.write_video_audio = load_dependencies()

    def generate(self, **kwargs) -> dict:
        """Validate at boundary, delegate, return output contract."""
        req = self.Input(**kwargs)
        return run_generate(self.pipe, self.write_video_audio, self.storage, req).model_dump()
