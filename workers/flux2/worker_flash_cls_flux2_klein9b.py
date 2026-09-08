from __future__ import annotations

import os
from typing import TYPE_CHECKING

from runpod_flash import Endpoint, GpuGroup

from workers.flux2._shared_flux2_klein9b import (
    Flux2Klein9bInput,
    do_inference,
    load_dependencies,
)

if TYPE_CHECKING:
    from workers.services.storage.storage import Storage


def generate(storage: Storage, pipe, torch_module, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract."""
    req = Flux2Klein9bInput(**kwargs)
    try:
        return do_inference(pipe, torch_module, storage, req).model_dump()
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


@Endpoint(
    name="flux2-klein9b-worker",
    gpu=[
        GpuGroup.AMPERE_16,
    ],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env={
        "SDNQ_USE_TRITON_MM": "0",
        "HF_TOKEN": os.environ.get("HF_TOKEN", ""),
        "HF_HOME": "/runpod-volume/huggingface-cache",
        "R2_BUCKET": os.environ.get("R2_BUCKET", "generated-media"),
        "R2_ENDPOINT": os.environ.get("R2_ENDPOINT", ""),
        "R2_ACCESS_KEY": os.environ.get("R2_ACCESS_KEY", ""),
        "R2_SECRET_KEY": os.environ.get("R2_SECRET_KEY", ""),
    },
    dependencies=[
        "torch==2.9.1",
        "diffusers==0.40.0",
        "transformers==5.16.1",
        "accelerate==1.14.0",
        "sdnq==0.2.6",
        "safetensors==0.8.0",
        "huggingface_hub==1.29.0",
        "pillow==12.3.0",
        "boto3==1.43.83",
    ],
)
class FluxKleinWorker:
    Input = Flux2Klein9bInput

    def __init__(self):
        self.storage, self.pipe, self.torch_module = load_dependencies()

    def generate(self, **kwargs) -> dict:
        """Validate at boundary, delegate, return output contract."""
        return generate(self.storage, self.pipe, self.torch_module, **kwargs)
