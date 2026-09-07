from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING

import modal

from workers.tiny_sd._shared_tiny_sd import (
    TinySDInput,
    do_inference,
    load_dependencies,
)

if TYPE_CHECKING:
    from workers.services.storage.storage import Storage


app = modal.App("tiny-sd-worker")

_INFERENCE_LOCK = threading.Lock()


def generate(storage: Storage, pipe, torch_module, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract."""
    req = TinySDInput(**kwargs)
    try:
        with _INFERENCE_LOCK:
            return do_inference(pipe, torch_module, storage, req).model_dump()
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


dotenv_secret = modal.Secret.from_dotenv(str(Path(__file__).parent.parent / ".env"))
hf_cache_vol = modal.Volume.from_name("hf-cache", create_if_missing=True)


image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg", "libgl1", "libglib2.0-0")
    .pip_install(
        "torch==2.9.1",
        "transformers==5.16.1",
        "accelerate==1.14.0",
        "diffusers==0.40.0",
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
    .add_local_python_source("workers.services", "workers.tiny_sd")
)


@app.cls(
    image=image,
    gpu="L4",
    secrets=[dotenv_secret],
    volumes={"/root/.cache/huggingface": hf_cache_vol},
    timeout=300,
    memory=32768,
    scaledown_window=150,
    max_containers=1,
)
class TinySDWorker:
    def __init__(self):
        pass

    @modal.enter()
    def load(self):
        self.storage, self.pipe, self.torch_module = load_dependencies()

    @modal.method()
    def generate(self, **kwargs) -> dict:
        """Validate at boundary, delegate, return output contract."""
        return generate(self.storage, self.pipe, self.torch_module, **kwargs)
