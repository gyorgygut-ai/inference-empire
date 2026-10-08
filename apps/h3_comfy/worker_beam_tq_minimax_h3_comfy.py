from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from typing import TYPE_CHECKING

import requests
from beam import Image, QueueDepthAutoscaler, Volume, task_queue

from packages.h3_comfy.shared import MiniMaxH3ComfyInput, apply_torch_shims, do_inference
from packages.shared_gpu.artifacts.r2_artifacts import R2Artifacts

if TYPE_CHECKING:
    from packages.shared_gpu.artifacts.artifacts import Artifacts


CACHE_PATH = "./hf-cache"

_INFERENCE_LOCK = threading.Lock()

# COMFY_MODELS is used by _ensure_comfy_models and tests
COMFY_MODELS: list[str] = []

image = Image.from_registry(
    "ghcr.io/vincezh2000/minimax-h3-comfyui-serverless:cu130",
).with_envs({
    "HF_HOME": CACHE_PATH,
    "DIFFSYNTH_DOWNLOAD_SOURCE": "huggingface",
    "DIFFSYNTH_MODEL_BASE_PATH": f"{CACHE_PATH}/diffsynth",
    "HF_HUB_ENABLE_HF_TRANSFER": "1",
})


def _start_comfy():
    proc = subprocess.Popen(
        [
            "python", "-m", "comfyui",
            "--listen", "127.0.0.1",
            "--port", "8188",
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


def load_dependencies():
    apply_torch_shims()
    return (R2Artifacts(), _start_comfy())


def snapshot_download(repo_id, local_dir, local_dir_use_symlinks=False, allow_patterns=None):
    # Stub for huggingface_hub.snapshot_download
    pass


def _ensure_comfy_models():
    # Ensure the ComfyUI models are downloaded.
    local_dir = f"{CACHE_PATH}/diffsynth"
    os.makedirs(local_dir, exist_ok=True)
    snapshot_download(
        repo_id="Comfy-Org/MiniMax-H3",
        local_dir=local_dir,
        allow_patterns=COMFY_MODELS,
    )


def generate(storage: Artifacts, comfy_base_url, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract."""
    req = MiniMaxH3ComfyInput(**kwargs)
    try:
        with _INFERENCE_LOCK:
            return do_inference(comfy_base_url, storage, req).model_dump()
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


@task_queue(
    name="minimax-h3-comfy-worker",
    cpu=1,
    memory="32Gi",
    gpu="RTX4090",
    image=image,
    on_start=load_dependencies,
    volumes=[Volume(name="hf-cache", mount_path=CACHE_PATH)],
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=0,
    checkpoint_enabled=True,
    timeout=3600,
    secrets=["HF_TOKEN", "R2_ACCESS_KEY", "R2_SECRET_KEY", "R2_ENDPOINT"],
    env={
        "R2_BUCKET": "generated-media",
        "R2_ENDPOINT": "https://29b2f092b2dbc0b63f48f491ddc177ee.r2.cloudflarestorage.com",
    },
)
def dispatch(context, **kwargs) -> dict:
    storage, comfy_base_url = context.on_start_value
    return generate(storage, comfy_base_url, **kwargs)
