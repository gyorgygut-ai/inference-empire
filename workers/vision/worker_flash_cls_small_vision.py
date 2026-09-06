from __future__ import annotations

from typing import TYPE_CHECKING

from runpod_flash import Endpoint, GpuGroup

from workers.services.storage.r2_storage import require_storage
from workers.vision._shared_small_vision import (
    SmallVisionInput,
    SmallVisionOutput,
    load_dependencies,
    run_analyze,
)

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

    def __init__(self, storage: Storage):
        storage = require_storage(storage)
        self.storage = storage
        self.model, self.processor, self.analyze_prompt = load_dependencies()

    def analyze(self, **kwargs) -> dict:
        """Validate at boundary, delegate, return output contract."""
        try:
            req = self.Input(**kwargs)
            result = run_analyze(self.model, self.processor, self.analyze_prompt, req)
            return result.model_dump() if isinstance(result, SmallVisionOutput) else result
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"inference failed: {e}")
