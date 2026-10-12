from __future__ import annotations

from pathlib import Path

import modal

from apps.vision.shared.worker_vision import (
    IMAGE_PIP_DEPS,
    SmallVisionInput,
    do_inference,
    load_dependencies,
    resolve_analyze_prompt,
)
from packages.shared_gpu.guard import run_guarded
from packages.shared_gpu.platform import MODAL_HF_MOUNT, modal_env, modal_volume

app = modal.App("small-vision-worker")

dotenv_secret = modal.Secret.from_dotenv(str(Path(__file__).parent.parent.parent / ".env"))
hf_cache_vol = modal_volume()

def generate(model, processor, analyze_prompt, **kwargs) -> dict:
    return run_guarded(
        SmallVisionInput,
        kwargs,
        lambda req: do_inference(
            model, processor, resolve_analyze_prompt(analyze_prompt, req.prompt), req
        ),
    )

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(*IMAGE_PIP_DEPS)
    .env(modal_env())
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
class SmallVisionWorker:
    @modal.enter()
    def load(self):
        self.model, self.processor, self.analyze_prompt = load_dependencies()

    @modal.method()
    def generate(self, **kwargs) -> dict:
        return generate(self.model, self.processor, self.analyze_prompt, **kwargs)


@app.function(image=modal.Image.debian_slim().pip_install("fastapi[standard]==0.141.1"), timeout=300)
@modal.fastapi_endpoint(method="POST")
def generate_web(item: dict) -> dict:
    return SmallVisionWorker().generate.remote(**item)


