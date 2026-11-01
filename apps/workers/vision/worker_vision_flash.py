from __future__ import annotations

from dist.contract_vision import Input as SmallVisionInput
from runpod_flash import Endpoint, GpuGroup
from shared.platform import flash_env
from shared.worker_vision import (
    DEPENDENCIES,
    do_inference,
    load_pipeline_lazy,
    resolve_analyze_prompt,
)


@Endpoint(
    name="worker-vision",
    gpu=[GpuGroup.AMPERE_16],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env=flash_env(),
    dependencies=list(DEPENDENCIES),
)
class Qwen2VLVisionWorker:
    Input = SmallVisionInput

    def __init__(self):
        # Initialize as None for lazy loading
        self.model = None
        self.processor = None
        self.analyze_prompt = None

    def generate(self, **kwargs) -> dict:
        req = SmallVisionInput(**kwargs)
        if self.model is None:
            self.model, self.processor, self.analyze_prompt = load_pipeline_lazy()
        assert self.analyze_prompt is not None
        prompt = resolve_analyze_prompt(self.analyze_prompt, getattr(req, "prompt", None))
        return do_inference(self.model, self.processor, prompt, req).model_dump()
