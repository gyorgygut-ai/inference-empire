from __future__ import annotations

import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

import modal

from workers.flux2.generate_flux2_klein9b import (
    Flux2Klein9bInput,
    load_pipeline as shared_load_pipeline,
    run_generate,
)

from workers.services.storage.real_r2 import require_storage
if TYPE_CHECKING:
    from workers.services.storage.storage import Storage

app = modal.App("flux2-klein9b-worker")

START_TIME = time.time()


@app.local_entrypoint()
def main(
    prompt: str = "a cat sitting on a rocket ship",
    height: int = 512,
    width: int = 512,
    num_inference_steps: int = 4,
    seed: int = -1,
):
    import json

    worker = FluxKleinWorker()
    result = worker.generate.remote(
        prompt=prompt,
        height=height,
        width=width,
        num_inference_steps=num_inference_steps,
        seed=seed if seed >= 0 else None,
    )
    print(json.dumps(result, indent=2))


dotenv_secret = modal.Secret.from_dotenv(str(Path(__file__).parent.parent / ".env"))
hf_cache_vol = modal.Volume.from_name("hf-cache", create_if_missing=True)


image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg", "libgl1", "libglib2.0-0")
    .pip_install(
        "torch==2.9.1",
        "transformers>=5.0,<6",
        "accelerate==1.14.0",
        "diffusers==0.40.0",
        "sdnq==0.2.6",
        "boto3==1.43.83",
        "pillow==12.3.0",
        "fastapi[standard]==0.141.1",
        "hf_transfer==0.1.9",
    )
    .env(
        {
            "HF_HOME": "/root/.cache/huggingface",
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
        }
    )
    .add_local_python_source("workers.services", "workers.flux2")
)


@app.cls(
    image=image,
    gpu="L4",
    secrets=[dotenv_secret],
    volumes={"/root/.cache/huggingface": hf_cache_vol},
    timeout=600,
    memory=32768,
    scaledown_window=150,
    max_containers=1,
)
class FluxKleinWorker:
    def __init__(self, storage: Storage):
        storage = require_storage(storage)
        self.storage = storage

    @modal.enter()
    def load(self):
        self.pipe, self.torch_module = shared_load_pipeline()

    @modal.method()
    def generate(self, **kwargs) -> dict:
        """Validate at boundary, delegate, return output contract."""
        try:
            req = Flux2Klein9bInput(**kwargs)
            return run_generate(self.pipe, self.torch_module, self.storage, req).model_dump()
        except Exception as e:
            print(f"[ERR] {type(e).__name__}: {e}", flush=True)
            raise RuntimeError(f"inference failed: {e}")

    @modal.fastapi_endpoint(method="POST")
    def generate_web(self, item: Flux2Klein9bInput) -> dict:
        try:
            return run_generate(self.pipe, self.torch_module, self.storage, item).model_dump()
        except Exception as e:
            print(f"[ERR] {type(e).__name__}: {e}", flush=True)
            raise
