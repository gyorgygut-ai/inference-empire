import base64
import io
import os
import time
import uuid
from pathlib import Path
from typing import Literal, Optional

import boto3
from pydantic import BaseModel, ConfigDict, Field

from beam import Image, QueueDepthAutoscaler, Volume, task_queue


def _load_dotenv(path: Path) -> None:
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


_load_dotenv(Path(__file__).parent.parent / ".env")

CACHE_PATH = "./hf-cache"

image = (
    Image(python_version="python3.11")
    .add_python_packages([
        "torch==2.9.1",
        "diffusers==0.39.0",
        "transformers>=4.57,<5",
        "accelerate==1.14.0",
        "safetensors==0.8.0",
        "hf_transfer==0.1.9",
        "pillow==12.3.0",
        "protobuf==6.33.6",
        "opencv-python-headless==4.12.0.88",
        "peft==0.17.0",
        "boto3==1.43.83",
    ])
    .with_envs({
        "HF_HOME": CACHE_PATH,
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
        "HF_TOKEN": os.environ.get("HF_TOKEN", ""),
        "R2_ENDPOINT": "https://29b2f092b2dbc0b63f48f491ddc177ee.r2.cloudflarestorage.com",
        "R2_BUCKET": "generated-media",
    })
)


class Krea2Ref2ImgInput(BaseModel):
    model_config = ConfigDict(title="Krea2Ref2ImgInput")
    prompt: str
    reference_image: Optional[str] = Field(default=None)
    height: int = Field(default=768)
    width: int = Field(default=768)
    num_inference_steps: int = Field(default=8)
    guidance_scale: float = Field(default=0.0)
    seed: Optional[int] = Field(default=None)
    lora_scale: float = Field(default=1.0)
    face_crop: bool = Field(default=True)


def load_pipeline():
    import torch
    import torch.distributed as dist

    dist.is_available = lambda: False

    print("[INIT] loading model krea/Krea-2-Turbo", flush=True)
    t0 = time.time()

    # Krea-2-Turbo's Qwen3-VL text encoder config ships `rope_scaling: null`;
    # transformers 4.57.x reads it unguarded (modeling_qwen3_vl.py:297) and
    # crashes with `'NoneType' object has no attribute 'get'`.
    import transformers.models.qwen3_vl.modeling_qwen3_vl as _q3vl_modeling

    _orig_q3vl_rope_init = _q3vl_modeling.Qwen3VLTextRotaryEmbedding.__init__

    def _q3vl_safe_rope_init(self, config, device=None):
        if getattr(config, "rope_scaling", None) is None:
            config.rope_scaling = {
                "rope_type": "default",
                "mrope_section": [24, 20, 20],
            }
        _orig_q3vl_rope_init(self, config, device)

    _q3vl_modeling.Qwen3VLTextRotaryEmbedding.__init__ = _q3vl_safe_rope_init

    from diffusers import DiffusionPipeline
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer

    runtime_dir = Path(
        snapshot_download(
            "yijunwang2/krea2-reid",
            allow_patterns=[
                "pipeline.py",
                "face_crop.py",
                "models/*.onnx",
                "krea2_reid_rank32.safetensors",
            ],
            cache_dir=CACHE_PATH,
        )
    )

    token = os.environ.get("HF_TOKEN") or None

    # Krea-2-Turbo's tokenizer/ folder ships only tokenizer.json (no
    # vocab.json), and its tokenizer_config.json stores `extra_special_tokens`
    # as a raw list. Both break transformers 4.57.x.
    tokenizer = AutoTokenizer.from_pretrained(
        "krea/Krea-2-Turbo",
        subfolder="tokenizer",
        token=token,
        trust_remote_code=True,
        cache_dir=CACHE_PATH,
        extra_special_tokens={
            t: t
            for t in [
                "<|im_start|>",
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
        },
    )

    pipe = DiffusionPipeline.from_pretrained(
        "krea/Krea-2-Turbo",
        custom_pipeline=str(runtime_dir),
        torch_dtype=torch.bfloat16,
        token=token,
        trust_remote_code=True,
        tokenizer=None,
        cache_dir=CACHE_PATH,
    )
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


def _decode_image(base64_str: str):
    from PIL import Image as PILImage

    img = PILImage.open(io.BytesIO(base64.b64decode(base64_str)))
    return img.convert("RGB")


def _face_crop(img, runtime_dir: Path, margin: float = 0.4):
    import cv2
    import numpy as np

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

    from PIL import Image as PILImage

    return PILImage.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))


@task_queue(
    name="krea2-ref2img-worker",
    cpu=8,
    memory="64Gi",
    gpu="RTX5090",
    image=image,
    on_start=load_pipeline,
    volumes=[Volume(name="hf-cache", mount_path=CACHE_PATH)],
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=1800,
    checkpoint_enabled=True,
    timeout=3600,
    secrets=["HF_TOKEN", "R2_ACCESS_KEY", "R2_SECRET_KEY", "R2_ENDPOINT"],
    env={
        "PYTORCH_NVML_BASED_CUDA_CHECK": "0",
    },
)
def generate(
    context,
    prompt: str,
    storage,
    reference_image: Optional[str] = None,
    height: int = 768,
    width: int = 768,
    num_inference_steps: int = 8,
    guidance_scale: float = 0.0,
    seed: Optional[int] = None,
    lora_scale: float = 1.0,
    face_crop: bool = True,
):
    pipe, runtime_dir, torch = context.on_start_value
    try:
        return _run_generate(
            pipe,
            runtime_dir,
            torch,
            prompt=prompt,
            storage=storage,
            reference_image=reference_image,
            height=height,
            width=width,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            seed=seed,
            lora_scale=lora_scale,
            face_crop=face_crop,
        )
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise


def _run_generate(
    pipe,
    runtime_dir,
    torch,
    prompt: str,
    storage,
    reference_image: Optional[str] = None,
    height: int = 768,
    width: int = 768,
    num_inference_steps: int = 8,
    guidance_scale: float = 0.0,
    seed: Optional[int] = None,
    lora_scale: float = 1.0,
    face_crop: bool = True,
) -> dict:
    """Pure sync generate logic - testable via DI. Tests call this directly."""
    t_req = time.time()
    n_files = 1 if reference_image else 0
    print(f"[REQ] prompt={prompt[:40]}  seed={seed}  files={n_files}", flush=True)
    req = Krea2Ref2ImgInput(
        prompt=prompt,
        reference_image=reference_image,
        height=height,
        width=width,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        seed=seed,
        lora_scale=lora_scale,
        face_crop=face_crop,
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
        base_kwargs["generator"] = torch.Generator(device="cpu").manual_seed(
            req.seed
        )

    print(f"[GEN] starting inference prompt={prompt[:40]}", flush=True)
    t_gen = time.time()

    if req.reference_image:
        ref = _decode_image(req.reference_image)
        if req.face_crop:
            ref = _face_crop(ref, runtime_dir)
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

    print(f"[GEN] inference done in {time.time() - t_gen:.1f}s  shape={gen_image.size[0] if hasattr(gen_image, 'size') else 'unknown'}x{gen_image.size[1] if hasattr(gen_image, 'size') else 'unknown'}", flush=True)
    gen_image = result.images[0]
    buffer = io.BytesIO()
    gen_image.save(buffer, format="PNG")
    file_bytes = buffer.getvalue()

    key = f"krea2_{uuid.uuid4()}.png"
    if storage is None:
        from services.real_r2 import RealR2Storage
        storage = RealR2Storage()
    storage.put(key, file_bytes)
    presigned_url = storage.presigned_url(key)
    print(f"[R2] uploaded key={key} url={presigned_url[:60]}", flush=True)

    print(f"[OK] completed in {time.time() - t_req:.1f}s", flush=True)
    return {"artifact": {"presigned_url": presigned_url}}
