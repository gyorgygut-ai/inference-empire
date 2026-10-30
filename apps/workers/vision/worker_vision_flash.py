from __future__ import annotations

from runpod_flash import Endpoint, GpuGroup
from dist.contract_vision import Input as SmallVisionInput
from shared.platform import flash_env
from shared.worker_vision import (
    DEPENDENCIES,
    do_inference,
    load_dependencies,
    resolve_analyze_prompt,
)


@Endpoint(
    name="workers-vision",
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
        self.model, self.processor, self.analyze_prompt = load_dependencies()

    def generate(self, **kwargs) -> dict:
        req = SmallVisionInput(**kwargs)
        prompt = resolve_analyze_prompt(self.analyze_prompt, getattr(req, "prompt", None))
        return do_inference(self.model, self.processor, prompt, req).model_dump()
