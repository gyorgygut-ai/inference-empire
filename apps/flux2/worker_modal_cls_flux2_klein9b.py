from __future__ import annotations

from functools import partial
from pathlib import Path

import modal

from apps.flux2.shared.worker_flux2 import (
    IMAGE_PIP_DEPS,
    Flux2Klein9bInput,
    do_inference,
    load_dependencies,
)
from packages.shared_gpu.guard import run_guarded
from packages.shared_gpu.platform import MODAL_HF_MOUNT, modal_env, modal_volume

app = modal.App("flux2-klein9b-worker")


def generate(storage, pipe, torch_module, **kwargs) -> dict:
    return run_guarded(
        Flux2Klein9bInput, kwargs, partial(do_inference, pipe, torch_module, storage)
    )


dotenv_secret = modal.Secret.from_dotenv(str(Path(__file__).parent.parent.parent / ".env"))
hf_cache_vol = modal_volume()

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg", "libgl1", "libglib2.0-0")
    .pip_install(*IMAGE_PIP_DEPS)
    .env(modal_env(extra={"SDNQ_USE_TRITON_MM": "0"}))
)

@app.cls(
    image=image,
    gpu="L4",
    secrets=[dotenv_secret],
    volumes={MODAL_HF_MOUNT: hf_cache_vol},
    timeout=300,
    memory=32768,
    scaledown_window=150,
    max_containers=1,
)
class FluxKleinWorker:
    @modal.enter()
    def load(self):
        self.storage, self.pipe, self.torch_module = load_dependencies()

    @modal.method()
    def generate(self, **kwargs) -> dict:
        return generate(self.storage, self.pipe, self.torch_module, **kwargs)


