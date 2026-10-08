from __future__ import annotations

from typing import TYPE_CHECKING

from runpod_flash import Endpoint, GpuGroup

from apps.krea2._shared_krea2_ref2img import (
    IMAGE_PIP_DEPS,
    Krea2Ref2ImgInput,
    do_inference,
    load_dependencies,
)

if TYPE_CHECKING:
    from packages.shared_gpu.artifacts.storage import Storage


def generate(storage: Storage, pipe, runtime_dir, torch_module, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract."""
    req = Krea2Ref2ImgInput(**kwargs)
    try:
        return do_inference(pipe, runtime_dir, torch_module, storage, req).model_dump()
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


@Endpoint(
    name="krea2-ref2img-worker",
    gpu=[GpuGroup.AMPERE_48, GpuGroup.ADA_48_PRO],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env={
        "HF_HOME": "/runpod-volume/huggingface-cache",
        "PYTORCH_NVML_BASED_CUDA_CHECK": "0",
    },
    dependencies=list(IMAGE_PIP_DEPS),
)
class Krea2Ref2ImgWorker:
    Input = Krea2Ref2ImgInput

    def __init__(self):
        self.storage, self.pipe, self.runtime_dir, self.torch_module = load_dependencies()

    def generate(self, **kwargs) -> dict:
        """Validate at boundary, delegate, return output contract."""
        return generate(self.storage, self.pipe, self.runtime_dir, self.torch_module, **kwargs)
