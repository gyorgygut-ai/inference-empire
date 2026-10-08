from __future__ import annotations

import os
from functools import partial

import modal
import requests

from packages.h3_comfy.shared import (
    MiniMaxH3ComfyInput,
    _start_comfy,
    apply_torch_shims,
    do_inference,
)
from packages.modal_bridge import attach_bridge
from packages.shared_gpu.guard import run_guarded
from packages.shared_gpu.platform import MODAL_HF_MOUNT, modal_env, modal_volume
from packages.shared_gpu.artifacts.r2_artifacts import R2Artifacts

app = modal.App("minimax-h3-comfy-worker")

# COMFY_MODELS is used by _ensure_comfy_models and tests
COMFY_MODELS: list[str] = []

r2_secret = modal.Secret.from_name(
    "r2-creds", required_keys=["R2_BUCKET", "R2_ENDPOINT", "R2_ACCESS_KEY", "R2_SECRET_KEY"]
)
hf_cache_vol = modal_volume()

image = (
    modal.Image.from_registry("ghcr.io/vincezh2000/minimax-h3-comfyui-serverless:cu130")
    .env(
        {
            **modal_env(),
            "DIFFSYNTH_DOWNLOAD_SOURCE": "huggingface",
            "DIFFSYNTH_MODEL_BASE_PATH": f"{MODAL_HF_MOUNT}/diffsynth",
        }
    )
    .add_local_python_source("apps", "apps")
    .add_local_python_source("packages", "packages")
)


def snapshot_download(repo_id, local_dir, local_dir_use_symlinks=False, allow_patterns=None):
    # Stub for huggingface_hub.snapshot_download
    _ = (repo_id, local_dir, local_dir_use_symlinks, allow_patterns)


def _ensure_comfy_models():
    # Ensure the ComfyUI models are downloaded.
    local_dir = f"{MODAL_HF_MOUNT}/diffsynth"
    os.makedirs(local_dir, exist_ok=True)
    snapshot_download(
        repo_id="Comfy-Org/MiniMax-H3",
        local_dir=local_dir,
        allow_patterns=COMFY_MODELS,
    )


def generate(storage, comfy_base_url: str, **kwargs) -> dict:
    return run_guarded(
        MiniMaxH3ComfyInput,
        kwargs,
        partial(do_inference, comfy_base_url, storage),
    )


@app.cls(
    image=image,
    gpu="L4",
    secrets=[r2_secret],
    volumes={MODAL_HF_MOUNT: hf_cache_vol},
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
        self.storage = R2Artifacts()
        self.comfy_base_url = _start_comfy()

    @modal.method()
    def generate(self, **kwargs) -> dict:
        return generate(self.storage, self.comfy_base_url, **kwargs)


attach_bridge(app, "MiniMaxH3ComfyWorker")
