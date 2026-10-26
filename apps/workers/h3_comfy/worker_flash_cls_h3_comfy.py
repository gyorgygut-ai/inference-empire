from __future__ import annotations

from functools import partial

from runpod_flash import Endpoint, GpuGroup
from shared.worker_h3_comfy import (
    MiniMaxH3ComfyInput,
    do_inference,
    load_dependencies,
)

from packages.workers.shared_gpu.guard import run_guarded
from packages.workers.shared_gpu.platform import flash_env


def generate(storage, comfy_base_url: str, **kwargs) -> dict:
    return run_guarded(
        MiniMaxH3ComfyInput,
        kwargs,
        partial(do_inference, comfy_base_url, storage),
    )


@Endpoint(
    name="workers-h3_comfy",
    gpu=[GpuGroup.AMPERE_48, GpuGroup.ADA_48_PRO],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env=flash_env(),
)
class MiniMaxH3ComfyWorker:
    Input = MiniMaxH3ComfyInput

    def __init__(self):
        self.storage, self.comfy_base_url = load_dependencies()

    def generate(self, **kwargs) -> dict:
        return generate(self.storage, self.comfy_base_url, **kwargs)
