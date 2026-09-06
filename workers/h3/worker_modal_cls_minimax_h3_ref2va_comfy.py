from __future__ import annotations

import modal
from pathlib import Path

from workers.h3._shared_minimax_h3_ref2va_comfy import ValidatedRef2VAComfyInput, do_inference, load_dependencies

app = modal.App("minimax-h3-ref2va-comfy-worker")

def generate(storage, **kwargs) -> dict:
    req = ValidatedRef2VAComfyInput(**kwargs)
    return do_inference(storage, req).model_dump()

@app.cls(image=modal.Image.debian_slim(), gpu="L4", max_containers=1)
class MiniMaxH3Ref2VAComfyWorker:
    def __init__(self):
        pass

    @modal.enter()
    def load(self):
        self.storage, = load_dependencies()

    @modal.method()
    def generate(self, **kwargs) -> dict:
        return generate(self.storage, **kwargs)
