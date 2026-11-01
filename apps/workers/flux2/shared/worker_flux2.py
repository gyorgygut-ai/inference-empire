from __future__ import annotations

import importlib
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from dist.contract_flux2 import Artifact
from dist.contract_flux2 import Input as Flux2Klein9bInput
from dist.contract_flux2 import Output as Flux2Klein9bOutput

from .validation import validate_image_b64

if TYPE_CHECKING:
    from diffusers import Flux2KleinPipeline

    from .artifacts import Artifacts

MODEL_CACHES = {
    "flux2_klein9b_sdnq4": {
        "url": "https://huggingface.co/Disty0/FLUX.2-klein-9B-SDNQ-4bit-dynamic-svd-r32",
        "path": "./model-cache/flux2_klein9b_sdnq4",
    }
}
MODEL_NAME = "flux2_klein9b_sdnq4"
MODEL_ID = urlparse(MODEL_CACHES[MODEL_NAME]["url"]).path.strip("/")
_MAX_WIDTH = 2560
_MAX_HEIGHT = 2560

DEPENDENCIES = [
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

def model_volumes():
    from beam import Volume

    return [
        Volume(name=f"model-cache-{name}", mount_path=model["path"])
        for name, model in MODEL_CACHES.items()
    ]


def download_models() -> dict[str, Path]:
    """Download declared models into their mounted cache paths."""
    import os

    from huggingface_hub import snapshot_download

    token = os.environ["SECRET_HUGGINGFACE_TOKEN"]
    return {
        name: Path(
            snapshot_download(
                repo_id=urlparse(model["url"]).path.strip("/"),
                cache_dir=model["path"],
                token=token,
            )
        )
        for name, model in MODEL_CACHES.items()
    }


def load_pipeline():
    """Production path: always boots the real model."""
    import torch.distributed as dist

    def _dist_unavailable() -> bool:
        return False

    dist.is_available = _dist_unavailable  # ty: ignore[invalid-assignment]

    import os

    import diffusers
    import torch

    print(f"[INIT] loading model {MODEL_ID}", flush=True)
    t0 = time.time()

    token = os.environ["SECRET_HUGGINGFACE_TOKEN"]

    # importing sdnq registers its quantizer with transformers
    from sdnq import SDNQConfig  # noqa: F401  # ty: ignore[unresolved-import]

    model_dir = download_models()[MODEL_NAME]
    pipe = diffusers.Flux2KleinPipeline.from_pretrained(
        str(model_dir),
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

def do_inference(pipe, torch_module, storage: Artifacts, req: Flux2Klein9bInput) -> Flux2Klein9bOutput:
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
        images.extend(prepare_image(req.input_image) for req in [req] if req.input_image)
    images.extend(prepare_image(ref) for ref in req.reference_images or [])
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

def load_pipeline_lazy():
    """Lazy load pipeline on first request (not at startup)."""
    import os

    import diffusers
    import torch

    print(f"[INIT] lazily loading model {MODEL_ID}", flush=True)
    t0 = time.time()

    token = os.environ["SECRET_HUGGINGFACE_TOKEN"]

    # importing sdnq registers its quantizer with transformers
    importlib.import_module("sdnq")

    model_dir = download_models()[MODEL_NAME]
    pipe = diffusers.Flux2KleinPipeline.from_pretrained(
        str(model_dir),
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

    if use_torch_compile and callable(apply_sdnq_options_to_model) and torch.cuda.is_available():
        pipe.transformer = apply_sdnq_options_to_model(
            pipe.transformer, use_quantized_matmul=True
        )
        pipe.text_encoder = apply_sdnq_options_to_model(
            pipe.text_encoder, use_quantized_matmul=True
        )

    print(f"[INIT] model loaded lazily in {time.time() - t0:.1f}s", flush=True)
    return pipe, torch
def load_dependencies():
    """Load all dependencies for flux2-klein9b worker (model loaded lazily)."""
    from .artifacts import R2Artifacts

    storage = R2Artifacts()
    # Model pipeline loaded lazily on first generate() request
    return storage, None, _TorchModuleService()


class _TorchModuleService:
    def __init__(self):
        import torch.distributed as dist

        def _dist_unavailable() -> bool:
            return False

        dist.is_available = _dist_unavailable  # ty: ignore[invalid-assignment]

    def __getattr__(self, name: str):
        import torch

        return getattr(torch, name)
