from __future__ import annotations

from functools import partial

from runpod_flash import Endpoint, GpuGroup
from shared.worker_h3_fl2va import (
    IMAGE_PIP_DEPS,
    MiniMaxH3TurboFl2vaInput,
    do_inference,
    load_dependencies,
)

from packages.workers.shared_gpu.guard import run_guarded
from packages.workers.shared_gpu.platform import flash_env


def generate(storage, pipe, write_video_audio, **kwargs) -> dict:
    return run_guarded(
        MiniMaxH3TurboFl2vaInput,
        kwargs,
        partial(do_inference, pipe, write_video_audio, storage),
    )


@Endpoint(
    name="workers-h3_fl2va",
    gpu=[GpuGroup.AMPERE_48, GpuGroup.ADA_48_PRO],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env=flash_env(),
    dependencies=list(IMAGE_PIP_DEPS),
)
class MiniMaxH3Fl2vaWorker:
    Input = MiniMaxH3TurboFl2vaInput

    def __init__(self):
        self.storage, self.pipe, self.write_video_audio = load_dependencies()

    def generate(self, **kwargs) -> dict:
        return generate(self.storage, self.pipe, self.write_video_audio, **kwargs)
