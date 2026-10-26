from __future__ import annotations

from functools import partial

from runpod_flash import Endpoint, GpuGroup
from shared.worker_flux2 import (
    Flux2Klein9bInput,
    do_inference,
    load_dependencies,
)

from packages.workers.shared_gpu.guard import run_guarded
from packages.workers.shared_gpu.platform import flash_env


def generate(storage, pipe, torch_module, **kwargs) -> dict:
    return run_guarded(
        Flux2Klein9bInput, kwargs, partial(do_inference, pipe, torch_module, storage)
    )


@Endpoint(
    name="workers-flux2",
    gpu=[
        GpuGroup.AMPERE_16,
    ],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env=flash_env(extra={"SDNQ_USE_TRITON_MM": "0"}),
)
class FluxKleinWorker:
    Input = Flux2Klein9bInput

    def __init__(self):
        self.storage, self.pipe, self.torch_module = load_dependencies()

    def generate(self, **kwargs) -> dict:
        return generate(self.storage, self.pipe, self.torch_module, **kwargs)
