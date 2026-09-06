from __future__ import annotations

import modal

from workers.vision._shared_small_vision import (
    REPO_ID,
    SmallVisionInput,
    SmallVisionOutput,
    do_inference,
    load_dependencies,
)

app = modal.App("small-vision-worker")


def generate(model, processor, analyze_prompt, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract."""
    req = SmallVisionInput(**kwargs)
    try:
        result = do_inference(model, processor, analyze_prompt, req)
        return result.model_dump() if isinstance(result, SmallVisionOutput) else result
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


def _download_model():
    import torch
    from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

    Qwen2VLForConditionalGeneration.from_pretrained(REPO_ID, torch_dtype=torch.bfloat16)
    AutoProcessor.from_pretrained(REPO_ID)


image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.9.1",
        "transformers>=5.0,<6",
        "torchvision==0.24.1",
        "pillow==12.3.0",
        "accelerate==1.14.0",
        "boto3==1.43.83",
        "fastapi==0.141.1",
        "hf_transfer==0.1.9",
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
    @modal.enter()
    def load(self):
        self.model, self.processor, self.analyze_prompt = load_dependencies()

    @modal.method()
    def analyze(self, **kwargs) -> dict:
        """Validate at boundary, delegate, return output contract."""
        return generate(self.model, self.processor, self.analyze_prompt, **kwargs)

    @modal.fastapi_endpoint(method="POST")
    def analyze_web(self, item: SmallVisionInput) -> dict:
        return self.analyze(**item.model_dump())
