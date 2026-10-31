from __future__ import annotations

import os

import modal
from dist.contract_flux2 import Input as Flux2Klein9bInput
from shared.platform import MODAL_HF_MOUNT, MODAL_IMAGE_IGNORE, modal_env, modal_volume
from shared.worker_flux2 import DEPENDENCIES, do_inference, load_dependencies

app = modal.App("workers-flux2")
runtime_secret = modal.Secret.from_dict(
    {
        "SECRET_HUGGINGFACE_TOKEN": os.environ["SECRET_HUGGINGFACE_TOKEN"],
        "SECRET_R2_ACCESS_KEY": os.environ["SECRET_R2_ACCESS_KEY"],
        "SECRET_R2_SECRET_KEY": os.environ["SECRET_R2_SECRET_KEY"],
        "SECRET_R2_ENDPOINT": os.environ["SECRET_R2_ENDPOINT"],
        "SECRET_R2_BUCKET": os.environ["SECRET_R2_BUCKET"],
    }
)
hf_cache_vol = modal_volume()

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(*DEPENDENCIES)
    .add_local_dir(".", remote_path="/root/bundle", copy=True, ignore=MODAL_IMAGE_IGNORE)
    .env(modal_env(extra={"PYTHONPATH": "/root/bundle", "SDNQ_USE_TRITON_MM": "0"}))
)

@app.cls(
    image=image,
    gpu="L4",
    secrets=[runtime_secret],
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
        req = Flux2Klein9bInput(**kwargs)
        return do_inference(self.pipe, self.torch_module, self.storage, req).model_dump()
