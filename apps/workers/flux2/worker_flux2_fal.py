from __future__ import annotations

from typing import ClassVar

import fal  # ty: ignore[unresolved-import]
from dist.contract_flux2 import Input as Flux2Klein9bInput  # noqa: TC002
from shared.worker_flux2 import DEPENDENCIES, do_inference, load_dependencies, load_pipeline_lazy


class FluxKleinWorker(fal.App):
    machine_type = "GPU-A100"
    requirements: ClassVar[list[str]] = list(DEPENDENCIES)
    secrets: ClassVar[list[str]] = [
        "SECRET_HUGGINGFACE_TOKEN",
        "SECRET_R2_ACCESS_KEY",
        "SECRET_R2_SECRET_KEY",
        "SECRET_R2_ENDPOINT",
        "SECRET_R2_BUCKET",
    ]
    min_concurrency = 0
    max_concurrency = 1
    keep_alive = 5

    def setup(self):
        self.storage, _, self.torch_module = load_dependencies()
        self.pipe = None

    @fal.endpoint("/generate")
    def generate(self, input: Flux2Klein9bInput) -> dict:
        if self.pipe is None:
            self.pipe, self.torch_module = load_pipeline_lazy()
        return do_inference(self.pipe, self.torch_module, self.storage, input).model_dump()
