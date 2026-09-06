from __future__ import annotations

from typing import TYPE_CHECKING

import modal

from workers.h3._shared_minimax_h3_fl2va import (
    MiniMaxH3Fl2VAInput,
    apply_torch_shims,
    do_inference,
    load_dependencies,
)
from workers.services.storage.r2_storage import require_storage

if TYPE_CHECKING:
    from workers.services.storage.storage import Storage

app = modal.App("minimax-h3-fl2va-worker")

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
        "diffusers==0.40.0",
        "transformers>=5.0,<6",
        "accelerate==1.14.0",
        "bitsandbytes",
        "pillow",
        "imageio==2.37.2",
        "imageio-ffmpeg==0.6.0",
        "torchaudio",
        "boto3==1.43.83",
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


def generate(storage: Storage, pipe, write_video_audio, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract."""
    req = MiniMaxH3Fl2VAInput(**kwargs)
    try:
        return do_inference(pipe, write_video_audio, storage, req).model_dump()
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


@app.cls(
    image=image,
    gpu="L4",
    secrets=[r2_secret],
    timeout=900,
    memory=32768,
    scaledown_window=150,
    max_containers=1,
)
class MiniMaxH3Fl2VAWorker:
    def __init__(self, storage: Storage):
        storage = require_storage(storage)
        self.storage = storage

    @modal.enter()
    def load(self):
        apply_torch_shims()
        self.pipe, self.write_video_audio = load_dependencies()

    @modal.method()
    def generate(self, **kwargs) -> dict:
        """Validate at boundary, delegate, return output contract."""
        return generate(self.storage, self.pipe, self.write_video_audio, **kwargs)

    @modal.fastapi_endpoint(method="POST")
    def generate_web(self, item: MiniMaxH3Fl2VAInput) -> dict:
        return generate(self.storage, self.pipe, self.write_video_audio, **item.model_dump())
