from __future__ import annotations

from typing import TYPE_CHECKING

from runpod_flash import Endpoint, GpuGroup

from apps.tiny_sd._shared_tiny_sd import (
    IMAGE_PIP_DEPS,
    TinySDInput,
    do_inference,
    load_dependencies,
)

if TYPE_CHECKING:
    from packages.shared_gpu.artifacts.storage import Storage


def generate(storage: Storage, pipe, torch_module, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract."""
    req = TinySDInput(**kwargs)
    try:
        return do_inference(pipe, torch_module, storage, req).model_dump()
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


@Endpoint(
    name="tiny-sd-worker",
    gpu=[
        GpuGroup.AMPERE_16,
    ],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env={
        "HF_HOME": "/runpod-volume/huggingface-cache",
    },
    dependencies=list(IMAGE_PIP_DEPS),
)
class TinySDWorker:
    Input = TinySDInput

    def __init__(self):
        self.storage, self.pipe, self.torch_module = load_dependencies()

    def generate(self, **kwargs) -> dict:
        """Validate at boundary, delegate, return output contract."""
        return generate(self.storage, self.pipe, self.torch_module, **kwargs)
