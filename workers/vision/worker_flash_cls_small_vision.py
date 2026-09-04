from __future__ import annotations

import os
from typing import TYPE_CHECKING

from runpod_flash import Endpoint, GpuGroup

from workers.vision.analyze_small_vision import (
    SmallVisionInput,
    SmallVisionOutput,
    load_models_as_needed,
    run_analyze,
)

from workers.services.storage.real_r2 import require_storage
if TYPE_CHECKING:
    from workers.services.storage.storage import Storage


@Endpoint(
    name="small-vision-worker",
    gpu=[GpuGroup.AMPERE_16],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env={
        "HF_HOME": "/runpod-volume/huggingface-cache",
    },
    dependencies=[
        "torch==2.9.1",
        "transformers>=4.57,<5",
        "torchvision",
        "pillow",
        "accelerate",
    ],
)
class Qwen2VLVisionWorker:
    Input = SmallVisionInput

    def __init__(self, storage: Storage, pipe=None):
        storage = require_storage(storage)
        self.storage = storage

        if pipe is not None:
            self.model, self.processor, self.analyze_prompt = load_models_as_needed(
                model=getattr(pipe, "model", None),
                processor=getattr(pipe, "processor", None),
            )
        else:
            self.model, self.processor, self.analyze_prompt = load_models_as_needed()

    def analyze(self, **kwargs) -> dict:
        """Validate at boundary, delegate, return output contract."""
        try:
            req = self.Input(**kwargs)
            result = run_analyze(self.model, self.processor, self.analyze_prompt, req)
            return result.model_dump() if isinstance(result, SmallVisionOutput) else result
        except Exception as e:
            raise RuntimeError(f"inference failed: {e}")
