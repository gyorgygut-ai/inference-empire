from __future__ import annotations

from functools import partial

from runpod_flash import Endpoint, GpuGroup
from shared.worker_h3_ref2va import (
    ValidatedRef2VAInput,
    do_inference,
    load_dependencies,
)

from packages.workers.shared_gpu.guard import run_guarded
from packages.workers.shared_gpu.platform import flash_env


def generate(storage, pipe, write_video_audio, **kwargs) -> dict:
    return run_guarded(
        ValidatedRef2VAInput,
        kwargs,
        partial(do_inference, pipe, write_video_audio, storage),
    )


@Endpoint(
    name="minimax-h3-ref2va-worker",
    gpu=[GpuGroup.AMPERE_48, GpuGroup.ADA_48_PRO],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env=flash_env(),
    dependencies=["diffusers==0.40.0", "transformers==5.16.1", "accelerate==1.14.0", "bitsandbytes==0.50.2"],
)
class MiniMaxH3Ref2vaWorker:
    Input = ValidatedRef2VAInput

    def __init__(self):
        self.storage, self.pipe, self.write_video_audio = load_dependencies()

    def generate(self, **kwargs) -> dict:
        return generate(self.storage, self.pipe, self.write_video_audio, **kwargs)
