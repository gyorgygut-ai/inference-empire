from __future__ import annotations

import os
from typing import TYPE_CHECKING

from runpod_flash import Endpoint, GpuGroup, PodTemplate

from workers.h3._shared_minimax_h3_ref2va import apply_torch_shims
from workers.h3._shared_minimax_h3_ref2va_comfy import (
    ValidatedRef2VAComfyInput,
    do_inference,
)
from workers.services.storage.r2_storage import R2Storage

if TYPE_CHECKING:
    from workers.services.storage.storage import Storage


def generate(storage: Storage, endpoint, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract."""
    req = ValidatedRef2VAComfyInput(**kwargs)
    try:
        return do_inference(endpoint, storage, req).model_dump()
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


def load_dependencies():
    return (
        Endpoint(
            name="minimax-h3-ref2va-comfy-backend",
            image="ghcr.io/vincezh2000/minimax-h3-comfyui-serverless:cu130",
            gpu=[GpuGroup.ADA_32_PRO],
        ),
    )


@Endpoint(
    name="minimax-h3-ref2va-comfy-worker",
    gpu=[GpuGroup.ADA_32_PRO],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    execution_timeout_ms=3600_000,
    template=PodTemplate(containerDiskInGb=150),
    dependencies=[
        "boto3==1.43.83",
        "pydantic==2.13.5",
    ],
    env={
        "HF_HOME": "/runpod-volume/huggingface-cache",
        "R2_BUCKET": os.environ.get("R2_BUCKET", "generated-media"),
        "R2_ENDPOINT": os.environ.get("R2_ENDPOINT", ""),
        "R2_ACCESS_KEY": os.environ.get("R2_ACCESS_KEY", ""),
        "R2_SECRET_KEY": os.environ.get("R2_SECRET_KEY", ""),
    },
)
class MiniMaxH3Ref2VAComfyWorker:
    Input = ValidatedRef2VAComfyInput

    def __init__(self):
        self.storage = R2Storage()
        apply_torch_shims()
        (self.endpoint,) = load_dependencies()

    def generate(self, **kwargs) -> dict:
        """Validate at boundary, delegate, return output contract."""
        return generate(self.storage, self.endpoint, **kwargs)
