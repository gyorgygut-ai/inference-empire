"""Shared business logic for flux2-klein9b. No platform imports."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from diffusers import Flux2KleinPipeline

    from workers.services.storage.storage import Storage
    from workers.services.torch_module.torch_module import TorchModule

MODEL_ID = "Disty0/FLUX.2-klein-9B-SDNQ-4bit-dynamic-svd-r32"
_MAX_WIDTH = 2560
_MAX_HEIGHT = 2560


def ensure_dotenv() -> None:
    """Load sibling workers/.env once (local runs; remote uses secrets)."""
    import os
    from pathlib import Path

    path = Path(__file__).parent.parent / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


class Flux2Klein9bInput(BaseModel):
    model_config = ConfigDict(title="Flux2Klein9bInput")
    prompt: str
    height: int = Field(default=512)
    width: int = Field(default=512)
    guidance_scale: float = Field(default=1.0)
    num_inference_steps: int = Field(default=4)
    seed: int | None = Field(default=None)
    input_image: str | None = Field(default=None)
    reference_images: list[str] = Field(default=[])


class Artifact(BaseModel):
    model_config = ConfigDict(title="Artifact")
    presigned_url: str


class Flux2Klein9bOutput(BaseModel):
    model_config = ConfigDict(title="Flux2Klein9bOutput")
    artifact: Artifact


def prepare_image(base64_str: str):
    import base64
    import io

    from PIL import Image

    img = Image.open(io.BytesIO(base64.b64decode(base64_str))).convert("RGB")
    w, h = img.size
    w = min(w - (w % 16), _MAX_WIDTH)
    h = min(h - (h % 16), _MAX_HEIGHT)
    if w != img.size[0] or h != img.size[1]:
        img = img.resize((w, h))
    return img


def load_pipeline():
    """Production path: always boots the real model."""
    import torch.distributed as dist

    dist.is_available = lambda: False

    import os

    import diffusers
    import torch

    print(f"[INIT] loading model {MODEL_ID}", flush=True)
    t0 = time.time()

    token = os.environ.get("HF_TOKEN")

    try:
        pipe = diffusers.Flux2KleinPipeline.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.bfloat16,
            token=token,
            local_files_only=True,
        )
    except OSError:
        pipe = diffusers.Flux2KleinPipeline.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.bfloat16,
            token=token,
        )
    pipe.to("cuda")

    from sdnq.common import use_torch_compile
    from sdnq.loader import apply_sdnq_options_to_model

    if use_torch_compile and torch.cuda.is_available():
        pipe.transformer = apply_sdnq_options_to_model(
            pipe.transformer, use_quantized_matmul=True
        )
        pipe.text_encoder = apply_sdnq_options_to_model(
            pipe.text_encoder, use_quantized_matmul=True
        )

    print(f"[INIT] model loaded in {time.time() - t0:.1f}s", flush=True)
    return pipe, torch


def load_pipeline_as_needed(pipe=None):
    """DI entry: injected fake passes through, else real load."""
    if pipe is not None:
        import torch

        return pipe, torch
    return load_pipeline()


def do_inference(pipe, torch_module, storage: Storage, req: Flux2Klein9bInput) -> Flux2Klein9bOutput:
    """Takes validated Input, returns Output. Testable via DI."""
    import io

    if storage is None:
        raise ValueError("storage is required")

    t_req = time.time()
    n_refs = (1 if req.input_image else 0) + len(req.reference_images or [])
    print(f"[REQ] prompt={req.prompt[:40]}  seed={req.seed}  files={n_refs}", flush=True)

    pipe_kwargs = {
        "prompt": req.prompt,
        "height": req.height,
        "width": req.width,
        "guidance_scale": req.guidance_scale,
        "num_inference_steps": req.num_inference_steps,
    }

    if req.seed is not None:
        pipe_kwargs["generator"] = torch_module.Generator(device="cuda").manual_seed(req.seed)

    images = []
    if req.input_image:
        images.append(prepare_image(req.input_image))
    for ref in req.reference_images or []:
        images.append(prepare_image(ref))
    if images:
        pipe_kwargs["image"] = images

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

    key = f"flux2_{uuid.uuid4()}.png"
    storage.put(key, file_bytes)
    url = storage.presigned_url(key)
    print(f"[R2] uploaded key={key} url={url[:60]}", flush=True)

    print(f"[OK] completed in {time.time() - t_req:.1f}s", flush=True)
    return Flux2Klein9bOutput(artifact=Artifact(presigned_url=url))


@dataclass
class Flux2Klein9bDeps:
    pipe: Flux2KleinPipeline
    torch_module: TorchModule


def pipe_factory() -> Flux2KleinPipeline:
    """Factory for the flux2 pipeline."""
    return load_pipeline()[0]


def load_dependencies():
    """Load all dependencies for flux2-klein9b worker."""
    from workers.services.torch_module.torch_module_service import TorchModuleService

    return pipe_factory(), TorchModuleService()
