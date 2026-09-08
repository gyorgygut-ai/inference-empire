from __future__ import annotations

import threading
from pathlib import Path

import modal

from workers.vision._shared_small_vision import (
    SmallVisionInput,
    do_inference,
    load_dependencies,
)

app = modal.App("small-vision-worker")

_INFERENCE_LOCK = threading.Lock()


def generate(model, processor, analyze_prompt, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract."""
    req = SmallVisionInput(**kwargs)
    try:
        with _INFERENCE_LOCK:
            result = do_inference(model, processor, analyze_prompt, req)
            return result.model_dump()
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


dotenv_secret = modal.Secret.from_dotenv(str(Path(__file__).parent.parent / ".env"))
hf_cache_vol = modal.Volume.from_name("hf-cache", create_if_missing=True)


image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.9.1",
        "transformers==5.16.1",
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
    .add_local_python_source("workers.services", "workers.vision")
)


@app.cls(
    image=image,
    gpu="L4",
    secrets=[dotenv_secret],
    volumes={"/root/.cache/huggingface": hf_cache_vol},
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
    def analyze(self, **kwargs) -> dict:
        """Validate at boundary, delegate, return output contract."""
        return generate(self.model, self.processor, self.analyze_prompt, **kwargs)
