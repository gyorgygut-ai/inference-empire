from __future__ import annotations

from runpod_flash import Endpoint, GpuGroup
from dist.contract_krea2 import Input as Krea2Ref2ImgInput
from shared.platform import flash_env
from shared.worker_krea2 import DEPENDENCIES, do_inference, load_dependencies


@Endpoint(
    name="workers-krea2",
    gpu=[GpuGroup.AMPERE_48, GpuGroup.ADA_48_PRO],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env=flash_env(extra={"PYTORCH_NVML_BASED_CUDA_CHECK": "0"}),
    dependencies=list(DEPENDENCIES),
)
class Krea2Ref2ImgWorker:
    Input = Krea2Ref2ImgInput

    def __init__(self):
        self.storage, self.pipe, self.runtime_dir, self.torch_module = load_dependencies()

    def generate(self, **kwargs) -> dict:
        req = Krea2Ref2ImgInput(**kwargs)
        return do_inference(self.pipe, self.runtime_dir, self.torch_module, self.storage, req).model_dump()
