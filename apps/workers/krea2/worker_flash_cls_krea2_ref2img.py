from __future__ import annotations

from functools import partial

from runpod_flash import Endpoint, GpuGroup

from apps.workers.krea2.shared.worker_krea2 import (
    Krea2Ref2ImgInput,
    do_inference,
    load_dependencies,
)
from packages.workers.shared_gpu.guard import run_guarded
from packages.workers.shared_gpu.platform import flash_env


def generate(storage, pipe, runtime_dir, torch_module, **kwargs) -> dict:
    return run_guarded(
        Krea2Ref2ImgInput,
        kwargs,
        partial(do_inference, pipe, runtime_dir, torch_module, storage),
    )


@Endpoint(
    name="workers-krea2",
    gpu=[GpuGroup.AMPERE_48, GpuGroup.ADA_48_PRO],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env=flash_env(extra={"PYTORCH_NVML_BASED_CUDA_CHECK": "0"}),
)
class Krea2Ref2ImgWorker:
    Input = Krea2Ref2ImgInput

    def __init__(self):
        self.storage, self.pipe, self.runtime_dir, self.torch_module = load_dependencies()

    def generate(self, **kwargs) -> dict:
        return generate(self.storage, self.pipe, self.runtime_dir, self.torch_module, **kwargs)
