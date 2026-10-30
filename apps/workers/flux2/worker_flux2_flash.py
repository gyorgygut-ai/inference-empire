from __future__ import annotations

from runpod_flash import Endpoint, GpuGroup
from dist.contract_flux2 import Input as Flux2Klein9bInput
from shared.platform import flash_env
from shared.worker_flux2 import DEPENDENCIES, do_inference, load_dependencies


@Endpoint(
    name="workers-flux2",
    gpu=[GpuGroup.AMPERE_16],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env=flash_env(extra={"SDNQ_USE_TRITON_MM": "0"}),
    dependencies=list(DEPENDENCIES),
)
class FluxKleinWorker:
    Input = Flux2Klein9bInput

    def __init__(self):
        self.storage, self.pipe, self.torch_module = load_dependencies()

    def generate(self, **kwargs) -> dict:
        req = Flux2Klein9bInput(**kwargs)
        return do_inference(self.pipe, self.torch_module, self.storage, req).model_dump()
