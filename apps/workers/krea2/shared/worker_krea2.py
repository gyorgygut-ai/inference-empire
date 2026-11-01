from __future__ import annotations

import importlib
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dist.contract_krea2 import Artifact
from dist.contract_krea2 import Input as Krea2Ref2ImgInput
from dist.contract_krea2 import Output as Krea2Ref2ImgOutput

from .validation import validate_image_b64

if TYPE_CHECKING:
    from diffusers import DiffusionPipeline

    from .artifacts import Artifacts

MODEL_REPO = "krea/Krea-2-Turbo"
REID_REPO = "yijunwang2/krea2-reid"
DEPENDENCIES = [
"torch==2.9.1",
"transformers==4.57.6",
"accelerate==1.14.0",
"diffusers==0.39.0",
"safetensors==0.8.0",
"huggingface-hub==0.36.2",
"pillow==12.3.0",
"boto3==1.43.83",
"fastapi[standard]==0.141.1",
"hf_transfer==0.1.9",
"protobuf",
"opencv-python-headless",
"peft",
]
EXTRA_SPECIAL_TOKENS = [    "<|im_start|>",
    "<|im_end|>",
    "<|object_ref_start|>",
    "<|object_ref_end|>",
    "<|box_start|>",
    "<|box_end|>",
    "<|quad_start|>",
    "<|quad_end|>",
    "<|vision_start|>",
    "<|vision_end|>",
    "<|vision_pad|>",
    "<|image_pad|>",
    "<|video_pad|>",
]

def _apply_qwen3_vl_rope_patch():
    import transformers.models.qwen3_vl.modeling_qwen3_vl as _q3vl_modeling

    _orig = _q3vl_modeling.Qwen3VLTextRotaryEmbedding.__init__

    def _safe_rope_init(self, config, device=None):
        if getattr(config, "rope_scaling", None) is None:
            config.rope_scaling = {
                "rope_type": "default",
                "mrope_section": [24, 20, 20],
            }
        _orig(self, config, device)

    _q3vl_modeling.Qwen3VLTextRotaryEmbedding.__init__ = _safe_rope_init


def _download_reid_runtime(cache_dir=None) -> Path:
    import os

    from huggingface_hub import snapshot_download

    snapshot_kwargs: dict[str, Any] = {
        "token": os.environ["SECRET_HUGGINGFACE_TOKEN"],
        "allow_patterns": [
            "pipeline.py",
            "face_crop.py",
            "models/*.onnx",
            "krea2_reid_rank32.safetensors",
        ],
    }
    if cache_dir:
        snapshot_kwargs["cache_dir"] = cache_dir
    return Path(snapshot_download(REID_REPO, **snapshot_kwargs))


def load_pipeline(cache_dir=None):
    """Production path: always boots the real model."""
    import torch.distributed as dist

    def _dist_unavailable() -> bool:
        return False

    dist.is_available = _dist_unavailable  # ty: ignore[invalid-assignment]

    print("[INIT] loading model krea/Krea-2-Turbo", flush=True)
    t0 = time.time()

    _apply_qwen3_vl_rope_patch()

    import os

    import torch
    from diffusers import DiffusionPipeline
    from transformers import AutoTokenizer

    runtime_dir = _download_reid_runtime(cache_dir)

    token = os.environ["SECRET_HUGGINGFACE_TOKEN"]

    tokenizer_kwargs = {
        "subfolder": "tokenizer",
        "token": token,
        "trust_remote_code": True,
        "extra_special_tokens": {t: t for t in EXTRA_SPECIAL_TOKENS},
    }
    if cache_dir:
        tokenizer_kwargs["cache_dir"] = cache_dir
    tokenizer = AutoTokenizer.from_pretrained(MODEL_REPO, **tokenizer_kwargs)

    pipe_kwargs = {
        "custom_pipeline": str(runtime_dir),
        "torch_dtype": torch.bfloat16,
        "token": token,
        "trust_remote_code": True,
        "tokenizer": None,
    }
    if cache_dir:
        pipe_kwargs["cache_dir"] = cache_dir
    pipe = DiffusionPipeline.from_pretrained(MODEL_REPO, **pipe_kwargs)
    pipe.tokenizer = tokenizer
    pipe.load_lora_weights(
        runtime_dir,
        weight_name="krea2_reid_rank32.safetensors",
        adapter_name="reid",
    )
    pipe.set_adapters(["reid"], weights=[1.0])
    pipe.enable_model_cpu_offload()
    print(f"[INIT] model loaded in {time.time() - t0:.1f}s", flush=True)
    return pipe, runtime_dir, torch

def decode_image(base64_str: str, field: str = "reference_image"):
    import base64
    import io

    from PIL import Image

    raw = validate_image_b64(base64_str, field)
    img = Image.open(io.BytesIO(base64.b64decode(raw)))
    return img.convert("RGB")

def face_crop(img, runtime_dir: Path, margin: float = 0.4):
    try:
        cv2 = importlib.import_module("cv2")
    except ImportError:
        cv2 = None
    import numpy as np
    from PIL import Image

    assert cv2 is not None

    onnx = any(runtime_dir.glob("models/*face*.onnx"))
    if not onnx:
        return img

    bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    detector = cv2.FaceDetectorYN_create(
        str(next(runtime_dir.glob("models/*face*.onnx"))),
        (bgr.shape[1], bgr.shape[0]),
        score_threshold=0.5,
    )
    _, faces = detector.detect(bgr)
    if faces is None or len(faces) == 0:
        return img

    x, y, w, h = (int(v) for v in faces[0][:4])
    pad_x = int(w * margin)
    pad_y = int(h * margin)
    x0 = max(x - pad_x, 0)
    y0 = max(y - pad_y, 0)
    x1 = min(x + w + pad_x, bgr.shape[1])
    y1 = min(y + h + pad_y, bgr.shape[0])
    crop = bgr[y0:y1, x0:x1]

    return Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))

def do_inference(
    pipe,
    runtime_dir,
    torch_module,
    storage: Artifacts,
    req: Krea2Ref2ImgInput,
) -> Krea2Ref2ImgOutput:
    """Takes validated Input, returns Output. Testable via DI."""
    import io

    t_req = time.time()
    print(
        f"[REQ] prompt={req.prompt[:40]}  seed={req.seed}  files={1 if req.reference_image else 0}",
        flush=True,
    )

    pipe.set_adapters(["reid"], weights=[req.lora_scale])

    base_kwargs = {
        "prompt": req.prompt,
        "width": req.width,
        "height": req.height,
        "num_inference_steps": req.num_inference_steps,
        "guidance_scale": req.guidance_scale,
    }
    if req.seed is not None:
        base_kwargs["generator"] = torch_module.Generator(device="cpu").manual_seed(req.seed)

    print(f"[GEN] starting inference prompt={req.prompt[:40]}", flush=True)
    t_gen = time.time()

    if req.reference_image:
        ref = decode_image(req.reference_image)
        if req.face_crop:
            ref = face_crop(ref, runtime_dir)
        result = pipe(
            **base_kwargs,
            image=ref,
            reference_max_pixels=384 * 384,
            vl_image_max_pixels=384 * 384,
            encode_reference_in_prompt=True,
            kv_cache=True,
        )
    else:
        result = pipe(**base_kwargs)

    image = result.images[0]
    size = image.size if hasattr(image, "size") else ("?", "?")
    print(
        f"[GEN] inference done in {time.time() - t_gen:.1f}s  shape={size[0]}x{size[1]}",
        flush=True,
    )
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    file_bytes = buffer.getvalue()

    key = f"krea2_{uuid.uuid4()}.png"
    storage.put(key, file_bytes)
    presigned_url = storage.presigned_url(key)
    print(f"[R2] uploaded key={key} url={presigned_url[:60]}", flush=True)

    print(f"[OK] completed in {time.time() - t_req:.1f}s", flush=True)
    return Krea2Ref2ImgOutput(artifact=Artifact(presigned_url=presigned_url))

def pipe_factory(cache_dir=None) -> DiffusionPipeline:
    """Factory for the krea2 pipeline."""
    return load_pipeline(cache_dir=cache_dir)[0]

def load_pipeline_lazy(cache_dir=None):
    """Lazy load pipeline on first request (not at startup)."""
    import os

    import torch
    from diffusers import DiffusionPipeline
    from transformers import AutoTokenizer

    print("[INIT] lazily loading model krea/Krea-2-Turbo", flush=True)
    t0 = time.time()

    _apply_qwen3_vl_rope_patch()

    runtime_dir = _download_reid_runtime(cache_dir)

    token = os.environ["SECRET_HUGGINGFACE_TOKEN"]

    tokenizer_kwargs = {
        "subfolder": "tokenizer",
        "token": token,
        "trust_remote_code": True,
        "extra_special_tokens": {t: t for t in EXTRA_SPECIAL_TOKENS},
    }
    if cache_dir:
        tokenizer_kwargs["cache_dir"] = cache_dir
    tokenizer = AutoTokenizer.from_pretrained(MODEL_REPO, **tokenizer_kwargs)

    pipe_kwargs = {
        "custom_pipeline": str(runtime_dir),
        "torch_dtype": torch.bfloat16,
        "token": token,
        "trust_remote_code": True,
        "tokenizer": None,
    }
    if cache_dir:
        pipe_kwargs["cache_dir"] = cache_dir
    pipe = DiffusionPipeline.from_pretrained(MODEL_REPO, **pipe_kwargs)
    pipe.tokenizer = tokenizer
    pipe.load_lora_weights(
        runtime_dir,
        weight_name="krea2_reid_rank32.safetensors",
        adapter_name="reid",
    )
    pipe.set_adapters(["reid"], weights=[1.0])
    pipe.enable_model_cpu_offload()
    print(f"[INIT] model loaded lazily in {time.time() - t0:.1f}s", flush=True)
    return pipe, runtime_dir, torch

def load_dependencies(cache_dir=None):
    """Load all dependencies for krea2 worker (model loaded lazily)."""
    from .artifacts import R2Artifacts

    storage = R2Artifacts()
    # Model pipeline loaded lazily on first generate() request
    return storage, None, None, _TorchModuleService()


class _TorchModuleService:
    def __init__(self):
        import torch.distributed as dist

        def _dist_unavailable() -> bool:
            return False

        dist.is_available = _dist_unavailable  # ty: ignore[invalid-assignment]

    def __getattr__(self, name: str):
        import torch

        return getattr(torch, name)
