from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import os
import shutil
import subprocess
import threading
import time
from typing import TYPE_CHECKING

import modal
import requests

from apps.h3_comfy._shared_minimax_h3_comfy import MiniMaxH3ComfyInput, apply_torch_shims, do_inference
from packages.storage.r2_storage import R2Storage

if TYPE_CHECKING:
    from packages.storage.storage import Storage

app = modal.App("minimax-h3-comfy-worker")

_INFERENCE_LOCK = threading.Lock()

# COMFY_MODELS is used by _ensure_comfy_models and tests
COMFY_MODELS: list[str] = []

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


def snapshot_download(repo_id, local_dir, local_dir_use_symlinks=False, allow_patterns=None):
    # Stub for huggingface_hub.snapshot_download
    pass


def _ensure_comfy_models():
    # Ensure the ComfyUI models are downloaded.
    local_dir = "/root/.cache/huggingface/diffsynth"
    os.makedirs(local_dir, exist_ok=True)
    snapshot_download(
        repo_id="Comfy-Org/MiniMax-H3",
        local_dir=local_dir,
        allow_patterns=COMFY_MODELS,
    )


def generate(storage: Storage, comfy_base_url: str, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract."""
    req = MiniMaxH3ComfyInput(**kwargs)
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
class MiniMaxH3ComfyWorker:
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
