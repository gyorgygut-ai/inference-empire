from __future__ import annotations

import os
from typing import TYPE_CHECKING

from runpod_flash import Endpoint, GpuGroup

from workers.flux2._shared_flux2_klein9b import (
    Flux2Klein9bInput,
    load_dependencies,
    run_generate,
)
from workers.services.storage.r2_storage import require_storage

if TYPE_CHECKING:
    from workers.services.storage.storage import Storage


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
        "diffusers",
        "transformers>=4.57,<5",
        "accelerate",
        "safetensors",
        "sdnq",
        "huggingface_hub",
        "pillow",
        "boto3",
    ],
)
class FluxKleinWorker:
    Input = Flux2Klein9bInput

    def __init__(self, storage: Storage):
        storage = require_storage(storage)
        self.storage = storage
        self.pipe, self.torch_module = load_dependencies()

    def generate(self, **kwargs) -> dict:
        """Validate at boundary, delegate, return output contract."""
        try:
            req = self.Input(**kwargs)
            return run_generate(self.pipe, self.torch_module, self.storage, req).model_dump()
        except Exception as e:  # noqa: BLE001
            print(f"[ERR] {type(e).__name__}: {e}", flush=True)
            raise RuntimeError(f"inference failed: {e}")
