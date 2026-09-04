from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import modal

from workers.krea2.generate_krea2_ref2img import (
    MODEL_REPO,
    REID_REPO,
    Krea2Ref2ImgInput,
    load_pipeline as shared_load_pipeline,
    run_generate,
)

from workers.services.storage.real_r2 import require_storage
if TYPE_CHECKING:
    from workers.services.storage.storage import Storage

app = modal.App("krea2-ref2img-worker")

dotenv_secret = modal.Secret.from_dotenv(str(Path(__file__).parent.parent / ".env"))
hf_cache_vol = modal.Volume.from_name("hf-cache", create_if_missing=True)


def _download_models():
    from huggingface_hub import snapshot_download
    import os

    token = os.environ.get("HF_TOKEN") or None

    snapshot_download(
        REID_REPO,
        token=token,
        allow_patterns=[
            "pipeline.py",
            "face_crop.py",
            "models/*.onnx",
            "krea2_reid_rank32.safetensors",
        ],
    )

    snapshot_download(MODEL_REPO, token=token)


image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg", "libgl1", "libglib2.0-0")
    .pip_install(
        "torch==2.9.1",
        "diffusers==0.39.0",
        "transformers>=4.57,<5",
        "accelerate==1.14.0",
        "safetensors==0.8.0",
        "huggingface-hub>=0.34,<2.0",
        "pillow==12.3.0",
        "protobuf==6.33.6",
        "opencv-python-headless==4.12.0.88",
        "peft==0.17.0",
        "boto3==1.43.83",
        "fastapi==0.141.1",
        "hf_transfer==0.1.9",
    )
    .env(
        {
            "HF_HOME": "/root/.cache/huggingface",
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "PYTORCH_NVML_BASED_CUDA_CHECK": "0",
        }
    )
    .add_local_python_source("workers.services", "workers.krea2")
)


@app.cls(
    image=image,
    gpu=["L40S", "A100-40GB"],
    secrets=[dotenv_secret],
    volumes={"/root/.cache/huggingface": hf_cache_vol},
    timeout=900,
    memory=65536,
    scaledown_window=150,
    max_containers=1,
)
class Krea2Ref2ImgWorker:
    def __init__(self, storage: Storage):
        storage = require_storage(storage)
        self.storage = storage

    @modal.enter()
    def load(self):
        print("[INIT] loading model krea/Krea-2-Turbo", flush=True)
        t0 = time.time()
        self.pipe, self.runtime_dir, self.torch_module = shared_load_pipeline()
        print(f"[INIT] model loaded in {time.time() - t0:.1f}s", flush=True)

    @modal.method()
    def generate(self, **kwargs) -> dict:
        """Validate at boundary, delegate, return output contract."""
        try:
            req = Krea2Ref2ImgInput(**kwargs)
            return run_generate(
                self.pipe, self.runtime_dir, self.torch_module, self.storage, req
            ).model_dump()
        except Exception as e:
            print(f"[ERR] {type(e).__name__}: {e}", flush=True)
            raise RuntimeError(f"inference failed: {e}")

    @modal.fastapi_endpoint(method="POST")
    def generate_web(self, item: Krea2Ref2ImgInput) -> dict:
        try:
            return run_generate(
                self.pipe, self.runtime_dir, self.torch_module, self.storage, item
            ).model_dump()
        except Exception as e:
            print(f"[ERR] {type(e).__name__}: {e}", flush=True)
            raise
