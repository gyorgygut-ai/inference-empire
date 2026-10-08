from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

import modal

from apps.krea2._shared_krea2_ref2img import (
    IMAGE_PIP_DEPS,
    Krea2Ref2ImgInput,
    do_inference,
    load_dependencies,
)
from packages.modal_bridge import attach_bridge

if TYPE_CHECKING:
    from packages.shared_gpu.artifacts.storage import Storage

app = modal.App("krea2-ref2img-worker")

_INFERENCE_LOCK = threading.Lock()


def generate(storage: Storage, pipe, runtime_dir, torch_module, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract."""
    req = Krea2Ref2ImgInput(**kwargs)
    try:
        with _INFERENCE_LOCK:
            return do_inference(pipe, runtime_dir, torch_module, storage, req).model_dump()
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
            "PYTORCH_NVML_BASED_CUDA_CHECK": "0",
        }
    )
    .add_local_python_source("apps", "apps")
    .add_local_python_source("packages", "packages")
)


@app.cls(
    image=image,
    gpu=["L40S", "A100-40GB"],
    secrets=[dotenv_secret],
    volumes={"/root/.cache/huggingface": hf_cache_vol},
    timeout=300,
    memory=65536,
    scaledown_window=150,
    max_containers=1,
)
class Krea2Ref2ImgWorker:
    @modal.enter()
    def load(self):
        print("[INIT] loading model krea/Krea-2-Turbo", flush=True)
        t0 = time.time()
        self.storage, self.pipe, self.runtime_dir, self.torch_module = load_dependencies()
        print(f"[INIT] model loaded in {time.time() - t0:.1f}s", flush=True)

    @modal.method()
    def generate(self, **kwargs) -> dict:
        """Validate at boundary, delegate, return output contract."""
        return generate(self.storage, self.pipe, self.runtime_dir, self.torch_module, **kwargs)


attach_bridge(app, "Krea2Ref2ImgWorker")
