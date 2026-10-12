from __future__ import annotations

from functools import partial
from pathlib import Path

import modal

from apps.h3_fl2va.shared.worker_h3_fl2va import (
    MiniMaxH3TurboFl2vaInput,
    apply_torch_shims,
    do_inference,
    load_dependencies,
)
from packages.shared_gpu.guard import run_guarded
from packages.shared_gpu.platform import MODAL_HF_MOUNT, modal_env, modal_volume

app = modal.App("minimax-h3-fl2va-worker")

dotenv_secret = modal.Secret.from_dotenv(str(Path(__file__).parent.parent.parent / ".env"))
hf_cache_vol = modal_volume()

def generate(storage, pipe, write_video_audio, **kwargs) -> dict:
    return run_guarded(
        MiniMaxH3TurboFl2vaInput,
        kwargs,
        partial(do_inference, pipe, write_video_audio, storage),
    )

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg", "libgl1", "libglib2.0-0")
    .pip_install(
        "torch==2.9.1",
        "torchcodec==0.9.0",
        "diffsynth[audio]==2.1.6",
        "diffusers==0.40.0",
        "transformers==5.16.1",
        "accelerate==1.14.0",
        "bitsandbytes==0.50.2",
        "pillow==12.3.0",
        "imageio==2.37.2",
        "imageio-ffmpeg==0.6.0",
        "torchaudio==2.9.1",
        "boto3==1.43.83",
        "fastapi==0.141.1",
        "hf_transfer==0.1.9",
    )
    .env(
        {
            **modal_env(),
            "DIFFSYNTH_DOWNLOAD_SOURCE": "huggingface",
            "DIFFSYNTH_MODEL_BASE_PATH": f"{MODAL_HF_MOUNT}/diffsynth",
        }
    )
)

@app.cls(
    image=image,
    gpu="L4",
    secrets=[dotenv_secret],
    volumes={MODAL_HF_MOUNT: hf_cache_vol},
    timeout=3600,
    memory=32768,
    scaledown_window=150,
    max_containers=1,
)
class MiniMaxH3Fl2VAWorker:
    def __init__(self):
        pass

    @modal.enter()
    def load(self):
        apply_torch_shims()
        self.storage, self.pipe, self.write_video_audio = load_dependencies()

    @modal.method()
    def generate(self, **kwargs) -> dict:
        return generate(self.storage, self.pipe, self.write_video_audio, **kwargs)


@app.function(image=modal.Image.debian_slim().pip_install("fastapi[standard]==0.141.1"), timeout=3600)
@modal.fastapi_endpoint(method="POST")
def generate_web(item: dict) -> dict:
    return MiniMaxH3Fl2VAWorker().generate.remote(**item)


