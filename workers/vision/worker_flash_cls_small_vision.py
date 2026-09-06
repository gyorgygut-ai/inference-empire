from __future__ import annotations

from runpod_flash import Endpoint, GpuGroup

from workers.vision._shared_small_vision import (
    SmallVisionInput,
    SmallVisionOutput,
    do_inference,
    load_dependencies,
)


def generate(model, processor, analyze_prompt, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract."""
    req = SmallVisionInput(**kwargs)
    try:
        result = do_inference(model, processor, analyze_prompt, req)
        return result.model_dump() if isinstance(result, SmallVisionOutput) else result
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
    dependencies=[
        "torch==2.9.1",
        "transformers==5.16.1",
        "torchvision==0.24.1",
        "accelerate==1.14.0",
        "pillow==12.3.0",
        "boto3==1.43.83",
    ],
)
class Qwen2VLVisionWorker:
    Input = SmallVisionInput

    def __init__(self):
        self.model, self.processor, self.analyze_prompt = load_dependencies()

    def analyze(self, **kwargs) -> dict:
        """Validate at boundary, delegate, return output contract."""
        return generate(self.model, self.processor, self.analyze_prompt, **kwargs)
