from __future__ import annotations

import os

import modal
from dist.contract_krea2 import Input as Krea2Ref2ImgInput
from shared.platform import MODAL_HF_MOUNT, MODAL_IMAGE_IGNORE, modal_env, modal_volume
from shared.worker_krea2 import DEPENDENCIES, do_inference, load_dependencies, load_pipeline_lazy

app = modal.App("worker-krea2")
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
    .env(modal_env(extra={"PYTHONPATH": "/root/bundle", "PYTORCH_NVML_BASED_CUDA_CHECK": "0"}))
)

@app.cls(
    image=image,
    gpu=["L40S", "A100-40GB"],
    secrets=[runtime_secret],
    volumes={MODAL_HF_MOUNT: hf_cache_vol},
    timeout=300,
    memory=65536,
    scaledown_window=150,
    max_containers=1,
)
class Krea2Ref2ImgWorker:
    @modal.enter()
    def load(self):
        self.storage, self.pipe, self.runtime_dir, self.torch_module = load_dependencies()
        # Initialize as None for lazy loading
        self.pipe = None
        self.torch_module = None

    @modal.method()
    def generate(self, **kwargs) -> dict:
        req = Krea2Ref2ImgInput(**kwargs)
        if self.pipe is None:
            self.pipe, self.runtime_dir = load_pipeline_lazy(cache_dir=self.runtime_dir)
        return do_inference(self.pipe, self.runtime_dir, self.torch_module, self.storage, req).model_dump()