from __future__ import annotations

import time
from typing import TYPE_CHECKING

import modal

from workers.h3._shared_minimax_h3_ref2va import (
    MiniMaxH3Ref2VAInput,
    ValidatedRef2VAInput,
    load_dependencies,
    run_generate,
)

from workers.services.storage.real_r2 import require_storage
if TYPE_CHECKING:
    from workers.services.storage.storage import Storage

app = modal.App("minimax-h3-ref2va-worker")

r2_secret = modal.Secret.from_name(
    "r2-creds", required_keys=["R2_BUCKET", "R2_ENDPOINT", "R2_ACCESS_KEY", "R2_SECRET_KEY"]
)


image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg", "libgl1", "libglib2.0-0")
    .pip_install(
        "torch==2.9.1",
        "torchcodec==0.9.0",
        "diffsynth[audio]",
        "transformers>=4.57,<5",
        "bitsandbytes",
        "pillow",
        "imageio[ffmpeg]",
        "torchaudio",
        "boto3",
        "fastapi",
        "hf_transfer",
    )
    .env(
        {
            "HF_HOME": "/root/.cache/huggingface",
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "DIFFSYNTH_DOWNLOAD_SOURCE": "huggingface",
            "DIFFSYNTH_MODEL_BASE_PATH": "/root/.cache/huggingface/diffsynth",
        }
    )
    .add_local_python_source("workers.services", "workers.h3")
)


@app.cls(
    image=image,
    gpu="L40S",
    secrets=[r2_secret],
    timeout=900,
    memory=65536,
    scaledown_window=150,
    max_containers=1,
)
class MiniMaxH3Ref2VAWorker:
    def __init__(self, storage: Storage):
        storage = require_storage(storage)
        self.storage = storage

    @modal.enter()
    def load(self):
        import torch.distributed as dist

        dist.is_available = lambda: False

        import torch
        _orig_load_library = torch.ops.load_library
        def _patched_load_library(path):
            try:
                return _orig_load_library(path)
            except OSError:
                pass
        torch.ops.load_library = _patched_load_library

        self.pipe, self.write_video_audio = load_dependencies()

    @modal.method()
    def generate(self, **kwargs) -> dict:
        try:
            req = ValidatedRef2VAInput(**kwargs)
            return run_generate(
                self.pipe, self.write_video_audio, self.storage, req
            ).model_dump()
        except Exception as e:
            print(f"[ERR] {type(e).__name__}: {e}", flush=True)
            raise

    @modal.fastapi_endpoint(method="POST")
    def generate_web(self, item: MiniMaxH3Ref2VAInput) -> dict:
        req = ValidatedRef2VAInput(**item.model_dump())
        return run_generate(
            self.pipe, self.write_video_audio, self.storage, req
        ).model_dump()
