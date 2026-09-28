"""Shared business logic for tiny-sd. No platform imports."""
from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from diffusers import StableDiffusionPipeline

    from packages.storage.storage import Storage

MODEL_ID = "segmind/tiny-sd"
_MAX_WIDTH = 1024
_MAX_HEIGHT = 1024

# Single source of truth for ALL provider image pip deps (modal/beam/flash).
# Worker files must reference this list, never inline their own pins.
# Pre-deploy gate: uv run python -c "from apps.tiny_sd._shared_tiny_sd import IMAGE_PIP_DEPS; print('\n'.join(IMAGE_PIP_DEPS))" | uv pip compile --python-version 3.11 -
IMAGE_PIP_DEPS: list[str] = [
    "torch==2.9.1",
    "transformers==5.16.1",
    "accelerate==1.14.0",
    "diffusers==0.40.0",
    "safetensors==0.8.0",
    "huggingface-hub==1.29.0",
    "pillow==12.3.0",
    "boto3==1.43.83",
    "fastapi[standard]==0.141.1",
    "hf_transfer==0.1.9",
]


class TinySDInput(BaseModel):
    model_config = ConfigDict(title="TinySDInput")
    prompt: str
    negative_prompt: str = Field(default="")
    height: int = Field(default=512)
    width: int = Field(default=512)
    num_inference_steps: int = Field(default=20)
    guidance_scale: float = Field(default=7.5)
    seed: int | None = Field(default=None)


class Artifact(BaseModel):
    model_config = ConfigDict(title="Artifact")
    presigned_url: str


class TinySDOutput(BaseModel):
    model_config = ConfigDict(title="TinySDOutput")
    artifact: Artifact


def load_pipeline():
    """Production path: always boots the real model."""
    import torch.distributed as dist

    def _dist_unavailable() -> bool:
        return False

    dist.is_available = _dist_unavailable

    import os

    import diffusers
    import torch

    print(f"[INIT] loading model {MODEL_ID}", flush=True)
    t0 = time.time()

    token = os.environ.get("HF_TOKEN")

    try:
        pipe = diffusers.StableDiffusionPipeline.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.float16,
            token=token,
            local_files_only=True,
        )
    except OSError:
        pipe = diffusers.StableDiffusionPipeline.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.float16,
            token=token,
        )
    pipe.to("cuda")

    print(f"[INIT] model loaded in {time.time() - t0:.1f}s", flush=True)
    return pipe, torch


def do_inference(pipe, torch_module, storage: Storage, req: TinySDInput) -> TinySDOutput:
    """Takes validated Input, returns Output. Testable via DI."""
    import io

    t_req = time.time()
    print(f"[REQ] prompt={req.prompt[:40]}  seed={req.seed}", flush=True)

    pipe_kwargs = {
        "prompt": req.prompt,
        "negative_prompt": req.negative_prompt,
        "height": req.height,
        "width": req.width,
        "num_inference_steps": req.num_inference_steps,
        "guidance_scale": req.guidance_scale,
    }

    if req.seed is not None:
        pipe_kwargs["generator"] = torch_module.Generator(device="cuda").manual_seed(req.seed)

    print(f"[GEN] starting inference prompt={req.prompt[:40]}", flush=True)
    t_gen = time.time()
    image = pipe(**pipe_kwargs).images[0]
    print(
        f"[GEN] inference done in {time.time() - t_gen:.1f}s  shape={image.size[0]}x{image.size[1]}",
        flush=True,
    )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    file_bytes = buffer.getvalue()

    key = f"tinysd_{uuid.uuid4()}.png"
    storage.put(key, file_bytes)
    url = storage.presigned_url(key)
    print(f"[R2] uploaded key={key} url={url[:60]}", flush=True)

    print(f"[OK] completed in {time.time() - t_req:.1f}s", flush=True)
    return TinySDOutput(artifact=Artifact(presigned_url=url))


def pipe_factory() -> StableDiffusionPipeline:
    """Factory for the tiny-sd pipeline."""
    return load_pipeline()[0]


def load_dependencies():
    """Load all dependencies for tiny-sd worker."""
    from packages.storage.r2_storage import R2Storage

    storage = R2Storage()
    return storage, pipe_factory(), _TorchModuleService()


class _TorchModuleService:
    def __init__(self):
        import torch.distributed as dist

        def _dist_unavailable() -> bool:
            return False

        dist.is_available = _dist_unavailable

    def __getattr__(self, name: str):
        import torch

        return getattr(torch, name)
