"""Shared business logic for flux2-klein9b. No platform imports."""
from __future__ import annotations

import importlib
import time
import uuid
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from apps.gpu_workers.services.media.validation import validate_image_b64

if TYPE_CHECKING:
    from diffusers import Flux2KleinPipeline

    from apps.gpu_workers.services.storage.storage import Storage

MODEL_ID = "Disty0/FLUX.2-klein-9B-SDNQ-4bit-dynamic-svd-r32"
_MAX_WIDTH = 2560
_MAX_HEIGHT = 2560

# Single source of truth for ALL provider image pip deps (modal/beam/flash).
# Worker files must reference this list, never inline their own pins.
# Pre-deploy gate: uv run python -c "from apps.gpu_workers.flux2._shared_flux2_klein9b import IMAGE_PIP_DEPS; print('\n'.join(IMAGE_PIP_DEPS))" | uv pip compile --python-version 3.11 -
IMAGE_PIP_DEPS: list[str] = [
    "torch==2.9.1",
    "transformers==5.16.1",
    "accelerate==1.14.0",
    "diffusers==0.40.0",
    "sdnq==0.2.6",
    "safetensors==0.8.0",
    "huggingface-hub==1.29.0",
    "pillow==12.3.0",
    "boto3==1.43.83",
    "fastapi[standard]==0.141.1",
    "hf_transfer==0.1.9",
]

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

    @field_validator("input_image")
    @classmethod
    def _check_input_image(cls, v: str | None, info: ValidationInfo) -> str | None:
        if v is None:
            return None
        return validate_image_b64(v, info.field_name)

    @field_validator("reference_images")
    @classmethod
    def _check_reference_images(cls, v: list[str], info: ValidationInfo) -> list[str]:
        return [validate_image_b64(item, f"{info.field_name}[{i}]") for i, item in enumerate(v)]

class Artifact(BaseModel):
    model_config = ConfigDict(title="Artifact")
    presigned_url: str

class Flux2Klein9bOutput(BaseModel):
    model_config = ConfigDict(title="Flux2Klein9bOutput")
    artifact: Artifact

def prepare_image(base64_str: str, field: str = "image"):
    import base64
    import io

    from PIL import Image

    raw = validate_image_b64(base64_str, field)
    img = Image.open(io.BytesIO(base64.b64decode(raw))).convert("RGB")
    w, h = img.size
    w = min(w - (w % 16), _MAX_WIDTH)
    h = min(h - (h % 16), _MAX_HEIGHT)
    if w != img.size[0] or h != img.size[1]:
        img = img.resize((w, h))
    return img

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
        pipe = diffusers.Flux2KleinPipeline.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.bfloat16,
            token=token,
            local_files_only=True,
            ignore_mismatched_sizes=True,
        )
    except OSError:
        pipe = diffusers.Flux2KleinPipeline.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.bfloat16,
            token=token,
            ignore_mismatched_sizes=True,
        )
    pipe.to("cuda")

    try:
        sdnq_common = importlib.import_module("sdnq.common")
        sdnq_loader = importlib.import_module("sdnq.loader")
        use_torch_compile = sdnq_common.use_torch_compile
        apply_sdnq_options_to_model = sdnq_loader.apply_sdnq_options_to_model
    except ImportError:
        use_torch_compile = None
        apply_sdnq_options_to_model = None

    assert use_torch_compile is not None
    assert apply_sdnq_options_to_model is not None

    if use_torch_compile and torch.cuda.is_available():
        pipe.transformer = apply_sdnq_options_to_model(
            pipe.transformer, use_quantized_matmul=True
        )
        pipe.text_encoder = apply_sdnq_options_to_model(
            pipe.text_encoder, use_quantized_matmul=True
        )

    print(f"[INIT] model loaded in {time.time() - t0:.1f}s", flush=True)
    return pipe, torch

def do_inference(pipe, torch_module, storage: Storage, req: Flux2Klein9bInput) -> Flux2Klein9bOutput:
    """Takes validated Input, returns Output. Testable via DI."""
    import io

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

def pipe_factory() -> Flux2KleinPipeline:
    """Factory for the flux2 pipeline."""
    return load_pipeline()[0]

def load_dependencies():
    """Load all dependencies for flux2-klein9b worker."""
    from apps.gpu_workers.services.storage.r2_storage import R2Storage
    from apps.gpu_workers.services.torch_module.torch_module_service import TorchModuleService

    storage = R2Storage()
    return storage, pipe_factory(), TorchModuleService()
