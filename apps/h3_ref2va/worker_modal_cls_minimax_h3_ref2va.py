from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import modal

from packages.h3_ref2va.shared import (
    ValidatedRef2VAInput,
    apply_torch_shims,
    do_inference,
    load_dependencies,
)
from packages.modal_bridge import attach_bridge

if TYPE_CHECKING:
    from packages.shared_gpu.artifacts.artifacts import Artifacts

app = modal.App("minimax-h3-ref2va-worker")

_INFERENCE_LOCK = threading.Lock()

r2_secret = modal.Secret.from_name(
    "r2-creds", required_keys=["R2_BUCKET", "R2_ENDPOINT", "R2_ACCESS_KEY", "R2_SECRET_KEY"]
)


image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg", "libgl1", "libglib2.0-0")
    .pip_install(
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
        "fastapi==0.141.1",
        "hf_transfer==0.1.9",
    )
    .env(
        {
            "HF_HOME": "/root/.cache/huggingface",
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "DIFFSYNTH_DOWNLOAD_SOURCE": "huggingface",
            "DIFFSYNTH_MODEL_BASE_PATH": "/root/.cache/huggingface/diffsynth",
        }
    )
    .add_local_python_source("apps", "apps")
    .add_local_python_source("packages", "packages")
)


def generate(storage: Artifacts, pipe, write_video_audio, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract."""
    req = ValidatedRef2VAInput(**kwargs)
    try:
        with _INFERENCE_LOCK:
            return do_inference(pipe, write_video_audio, storage, req).model_dump()
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


@app.cls(
    image=image,
    gpu="L40S",
    secrets=[r2_secret],
    timeout=3600,
    memory=65536,
    scaledown_window=150,
    max_containers=1,
)
class MiniMaxH3Ref2VAWorker:
    def __init__(self):
        pass

    @modal.enter()
    def load(self):
        apply_torch_shims()
        self.storage, self.pipe, self.write_video_audio = load_dependencies()

    @modal.method()
    def generate(self, **kwargs) -> dict:
        """Validate at boundary, delegate, return output contract."""
        return generate(self.storage, self.pipe, self.write_video_audio, **kwargs)


attach_bridge(app, "MiniMaxH3Ref2VAWorker")
