from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import threading
from pathlib import Path
from typing import TYPE_CHECKING

import modal

from apps.flux2._shared_flux2_klein9b import (
    IMAGE_PIP_DEPS,
    Flux2Klein9bInput,
    do_inference,
    load_dependencies,
)

if TYPE_CHECKING:
    from packages.storage.storage import Storage

app = modal.App("flux2-klein9b-worker")

_INFERENCE_LOCK = threading.Lock()


def generate(storage: Storage, pipe, torch_module, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract."""
    req = Flux2Klein9bInput(**kwargs)
    try:
        with _INFERENCE_LOCK:
            return do_inference(pipe, torch_module, storage, req).model_dump()
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


dotenv_secret = modal.Secret.from_dotenv(str(Path(__file__).parent.parent.parent / ".env"))
hf_cache_vol = modal.Volume.from_name("hf-cache", create_if_missing=True)


image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg", "libgl1", "libglib2.0-0")
    .pip_install(*IMAGE_PIP_DEPS)
    .env(
        {
            "HF_HOME": "/root/.cache/huggingface",
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "SDNQ_USE_TRITON_MM": "0",
        }
    )
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
class FluxKleinWorker:
    @modal.enter()
    def load(self):
        self.storage, self.pipe, self.torch_module = load_dependencies()

    @modal.method()
    def generate(self, **kwargs) -> dict:
        """Validate at boundary, delegate, return output contract."""
        return generate(self.storage, self.pipe, self.torch_module, **kwargs)
