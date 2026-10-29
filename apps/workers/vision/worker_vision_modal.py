from __future__ import annotations

import os

import modal
from shared.contract_vision import SmallVisionInput
from shared.platform import MODAL_HF_MOUNT, MODAL_IMAGE_IGNORE, modal_env, modal_volume
from shared.worker_vision import (
    DEPENDENCIES,
    do_inference,
    load_dependencies,
    resolve_analyze_prompt,
)

app = modal.App("workers-vision")
runtime_secret = modal.Secret.from_dict({"HF_TOKEN": os.environ["HF_TOKEN"]})
hf_cache_vol = modal_volume()

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(*DEPENDENCIES)
    .add_local_dir(".", remote_path="/root/bundle", copy=True, ignore=MODAL_IMAGE_IGNORE)
    .env(modal_env(extra={"PYTHONPATH": "/root/bundle"}))
)

@app.cls(
    image=image,
    gpu="L4",
    secrets=[runtime_secret],
    volumes={MODAL_HF_MOUNT: hf_cache_vol},
    timeout=300,
    memory=32768,
    scaledown_window=150,
    max_containers=1,
)
class SmallVisionWorker:
    @modal.enter()
    def load(self):
        self.model, self.processor, self.analyze_prompt = load_dependencies()

    @modal.method()
    def generate(self, **kwargs) -> dict:
        req = SmallVisionInput(**kwargs)
        prompt = resolve_analyze_prompt(self.analyze_prompt, getattr(req, "prompt", None))
        return do_inference(self.model, self.processor, prompt, req).model_dump()
