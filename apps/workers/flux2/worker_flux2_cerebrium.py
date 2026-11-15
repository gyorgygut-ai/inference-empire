from __future__ import annotations

import os
import threading

from dist.contract_flux2 import Artifact
from dist.contract_flux2 import Input as Flux2Klein9bInput
from dist.contract_flux2 import Output as Flux2Klein9bOutput
from shared.worker_flux2 import do_inference, load_dependencies, load_pipeline_lazy

__all__ = ["Artifact", "Flux2Klein9bInput", "Flux2Klein9bOutput", "generate"]

MODEL_CACHE_DIR = "/persistent-storage/worker-flux2"
_runtime_lock = threading.Lock()
_storage = None
_pipe = None
_torch_module = None


def generate(
    prompt: str,
    height: int = 512,
    width: int = 512,
    guidance_scale: float = 1.0,
    num_inference_steps: int = 4,
    seed: int | None = None,
    input_image: str | None = None,
    reference_images: list[str] | None = None,
) -> dict:
    global _pipe, _storage, _torch_module

    req = Flux2Klein9bInput(
        prompt=prompt,
        height=height,
        width=width,
        guidance_scale=guidance_scale,
        num_inference_steps=num_inference_steps,
        seed=seed,
        input_image=input_image,
        reference_images=reference_images or [],
    )
    with _runtime_lock:
        if _storage is None:
            _storage, _, _torch_module = load_dependencies()
        if _pipe is None:
            _pipe, _torch_module = load_pipeline_lazy(
                cache_dir=os.environ.get("FLUX2_MODEL_CACHE_DIR", MODEL_CACHE_DIR)
            )
        result = do_inference(_pipe, _torch_module, _storage, req)
    return result.model_dump()
