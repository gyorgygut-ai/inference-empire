from __future__ import annotations

from functools import partial

from runpod_flash import Endpoint, GpuGroup

from apps.tiny_sd.shared.worker_tiny_sd import (
    IMAGE_PIP_DEPS,
    TinySDInput,
    do_inference,
    load_dependencies,
)
from packages.shared_gpu.guard import run_guarded
from packages.shared_gpu.platform import flash_env


def generate(storage, pipe, torch_module, **kwargs) -> dict:
    return run_guarded(
        TinySDInput, kwargs, partial(do_inference, pipe, torch_module, storage)
    )


@Endpoint(
    name="tiny-sd-worker",
    gpu=[
        GpuGroup.AMPERE_16,
    ],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env=flash_env(),
    dependencies=list(IMAGE_PIP_DEPS),
)
class TinySDWorker:
    Input = TinySDInput

    def __init__(self):
        self.storage, self.pipe, self.torch_module = load_dependencies()

    def generate(self, **kwargs) -> dict:
        return generate(self.storage, self.pipe, self.torch_module, **kwargs)
