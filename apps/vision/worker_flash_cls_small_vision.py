from __future__ import annotations

from runpod_flash import Endpoint, GpuGroup

from apps.vision._shared_small_vision import (
    IMAGE_PIP_DEPS,
    SmallVisionInput,
    do_inference,
    load_dependencies,
    resolve_analyze_prompt,
)


def generate(model, processor, analyze_prompt, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract."""
    req = SmallVisionInput(**kwargs)
    try:
        result = do_inference(model, processor, resolve_analyze_prompt(analyze_prompt, req.prompt), req)
        return result.model_dump()
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


@Endpoint(
    name="small-vision-worker",
    gpu=[GpuGroup.AMPERE_16],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env={
        "HF_HOME": "/runpod-volume/huggingface-cache",
    },
    dependencies=list(IMAGE_PIP_DEPS),
)
class Qwen2VLVisionWorker:
    Input = SmallVisionInput

    def __init__(self):
        self.model, self.processor, self.analyze_prompt = load_dependencies()

    def analyze(self, **kwargs) -> dict:
        """Validate at boundary, delegate, return output contract."""
        return generate(self.model, self.processor, self.analyze_prompt, **kwargs)
