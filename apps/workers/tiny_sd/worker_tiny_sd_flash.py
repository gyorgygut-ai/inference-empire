from __future__ import annotations

from dist.contract_tiny_sd import Input as TinySDInput
from runpod_flash import Endpoint, GpuGroup
from shared.platform import flash_env
from shared.worker_tiny_sd import DEPENDENCIES, do_inference, load_dependencies


@Endpoint(
    name="workers-tiny_sd",
    gpu=[GpuGroup.AMPERE_16],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env=flash_env(),
    dependencies=list(DEPENDENCIES),
)
class TinySDWorker:
    Input = TinySDInput

    def __init__(self):
        self.storage, self.pipe, self.torch_module = load_dependencies()

    def generate(self, **kwargs) -> dict:
        req = TinySDInput(**kwargs)
        return do_inference(self.pipe, self.torch_module, self.storage, req).model_dump()
