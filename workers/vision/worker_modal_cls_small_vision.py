from __future__ import annotations

from typing import TYPE_CHECKING

import modal

from workers.vision.analyze_small_vision import (
    REPO_ID,
    SmallVisionInput,
    SmallVisionOutput,
    load_models as shared_load_models,
    run_analyze,
)

from workers.services.storage.real_r2 import require_storage
if TYPE_CHECKING:
    from workers.services.storage.storage import Storage

app = modal.App("small-vision-worker")


def _download_model():
    import torch
    from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

    Qwen2VLForConditionalGeneration.from_pretrained(REPO_ID, torch_dtype=torch.bfloat16)
    AutoProcessor.from_pretrained(REPO_ID)


image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.9.1",
        "transformers",
        "torchvision",
        "pillow",
        "accelerate",
        "fastapi",
        "hf_transfer",
    )
    .env(
        {
            "HF_HOME": "/root/.cache/huggingface",
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
        }
    )
    .run_function(_download_model)
    .add_local_python_source("workers.services", "workers.vision")
)


@app.cls(
    image=image,
    gpu="L4",
    timeout=600,
    scaledown_window=150,
    max_containers=1,
)
class SmallVisionWorker:
    def __init__(self, storage: Storage):
        storage = require_storage(storage)
        self.storage = storage

    @modal.enter()
    def load(self):
        self.model, self.processor, self.analyze_prompt = shared_load_models()

    def _run_analyze(self, req: SmallVisionInput):
        return run_analyze(self.model, self.processor, self.analyze_prompt, req)

    @modal.method()
    def analyze(self, **kwargs) -> dict:
        try:
            req = SmallVisionInput(**kwargs)
            result = self._run_analyze(req)
            return result.model_dump() if isinstance(result, SmallVisionOutput) else result
        except Exception as e:
            print(f"[ERR] {type(e).__name__}: {e}", flush=True)
            raise RuntimeError(f"inference failed: {e}")

    @modal.fastapi_endpoint(method="POST")
    def analyze_web(self, item: SmallVisionInput) -> dict:
        try:
            result = self._run_analyze(item)
            return result.model_dump() if isinstance(result, SmallVisionOutput) else result
        except Exception as e:
            print(f"[ERR] {type(e).__name__}: {e}", flush=True)
            raise
