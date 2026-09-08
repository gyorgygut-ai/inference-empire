from __future__ import annotations

import subprocess
import threading
import time
from typing import TYPE_CHECKING

import modal
import requests

from workers.h3._shared_minimax_h3_comfy import apply_torch_shims
from workers.h3._shared_minimax_h3_ref2va_comfy import (
    ValidatedRef2VAComfyInput,
    do_inference,
)
from workers.services.storage.r2_storage import R2Storage

if TYPE_CHECKING:
    from workers.services.storage.storage import Storage

app = modal.App("minimax-h3-ref2va-comfy-worker")

_INFERENCE_LOCK = threading.Lock()

r2_secret = modal.Secret.from_name(
    "r2-creds", required_keys=["R2_BUCKET", "R2_ENDPOINT", "R2_ACCESS_KEY", "R2_SECRET_KEY"]
)

image = (
    modal.Image.from_registry("ghcr.io/vincezh2000/minimax-h3-comfyui-serverless:cu130")
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


def _start_comfy():
    proc = subprocess.Popen(
        [
            "python",
            "-m",
            "comfyui",
            "--listen",
            "127.0.0.1",
            "--port",
            "8188",
            "--disable-auto-update",
            "--dont-print-server",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(60):
        try:
            r = requests.get("http://127.0.0.1:8188/system_stats", timeout=2)
            if r.status_code == 200:
                break
        except requests.ConnectionError:
            pass
        if proc.poll() is not None:
            raise RuntimeError(f"ComfyUI server exited with code {proc.returncode}")
        time.sleep(1)
    else:
        raise RuntimeError("ComfyUI server did not become ready within 60s")
    print("[INIT] ComfyUI server ready", flush=True)

    return "http://127.0.0.1:8188"


def generate(storage: Storage, comfy_base_url, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract."""
    req = ValidatedRef2VAComfyInput(**kwargs)
    try:
        with _INFERENCE_LOCK:
            return do_inference(comfy_base_url, storage, req).model_dump()
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


@app.cls(
    image=image,
    gpu="L4",
    secrets=[r2_secret],
    timeout=3600,
    memory=32768,
    scaledown_window=150,
    max_containers=1,
)
class MiniMaxH3Ref2VAComfyWorker:
    def __init__(self):
        pass

    @modal.enter()
    def load(self):
        apply_torch_shims()
        self.storage = R2Storage()
        self.comfy_base_url = _start_comfy()

    @modal.method()
    def generate(self, **kwargs) -> dict:
        """Validate at boundary, delegate, return output contract."""
        return generate(self.storage, self.comfy_base_url, **kwargs)
