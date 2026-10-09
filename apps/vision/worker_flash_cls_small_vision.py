from __future__ import annotations

from runpod_flash import Endpoint, GpuGroup

from apps.vision.shared.worker_vision import (
    IMAGE_PIP_DEPS,
    SmallVisionInput,
    do_inference,
    load_dependencies,
    resolve_analyze_prompt,
)
from packages.shared_gpu.guard import run_guarded
from packages.shared_gpu.platform import flash_env


def generate(model, processor, analyze_prompt, **kwargs) -> dict:
    return run_guarded(
        SmallVisionInput,
        kwargs,
        lambda req: do_inference(
            model, processor, resolve_analyze_prompt(analyze_prompt, req.prompt), req
        ),
    )


@Endpoint(
    name="small-vision-worker",
    gpu=[GpuGroup.AMPERE_16],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env=flash_env(),
    dependencies=list(IMAGE_PIP_DEPS),
)
class Qwen2VLVisionWorker:
    Input = SmallVisionInput

    def __init__(self):
        self.model, self.processor, self.analyze_prompt = load_dependencies()

    def generate(self, **kwargs) -> dict:
        return generate(self.model, self.processor, self.analyze_prompt, **kwargs)
