from __future__ import annotations

from pathlib import Path

import modal

from packages.modal_bridge import attach_bridge
from packages.shared_gpu.guard import run_guarded
from packages.shared_gpu.platform import MODAL_HF_MOUNT, modal_env, modal_volume
from packages.vision.shared import (
    IMAGE_PIP_DEPS,
    SmallVisionInput,
    do_inference,
    load_dependencies,
    resolve_analyze_prompt,
)

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
    .add_local_python_source("apps", "apps")
    .add_local_python_source("packages", "packages")
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


attach_bridge(app, "SmallVisionWorker")
