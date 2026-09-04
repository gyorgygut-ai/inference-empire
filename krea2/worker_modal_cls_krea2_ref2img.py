import base64
import io
import os
import time
import re
from pathlib import Path
from typing import Literal, Optional

import modal
from pydantic import BaseModel, ConfigDict, Field

MODEL_REPO = "krea/Krea-2-Turbo"
REID_REPO = "yijunwang2/krea2-reid"

app = modal.App("krea2-ref2img-worker")

dotenv_secret = modal.Secret.from_dotenv(str(Path(__file__).parent.parent / ".env"))
hf_cache_vol = modal.Volume.from_name("hf-cache", create_if_missing=True)


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


def _download_models():
    import os
    from huggingface_hub import snapshot_download

    token = os.environ.get("HF_TOKEN") or None

    # Download reid runtime and models
    snapshot_download(
        REID_REPO,
        token=token,
        allow_patterns=[
            "pipeline.py",
            "face_crop.py",
            "models/*.onnx",
            "krea2_reid_rank32.safetensors",
        ],
    )

    # Download main model
    snapshot_download(MODEL_REPO, token=token)


image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg", "libgl1", "libglib2.0-0")
    .pip_install(
        "torch==2.9.1",
        "diffusers==0.39.0",
        "transformers>=4.57,<5",
        "accelerate==1.14.0",
        "safetensors==0.8.0",
        "huggingface-hub>=0.34,<2.0",
        "pillow==12.3.0",
        "protobuf==6.33.6",
        "opencv-python-headless==4.12.0.88",
        "peft==0.17.0",
        "boto3==1.43.83",
        "fastapi==0.141.1",
        "hf_transfer==0.1.9",
    )
    .env(
        {
            "HF_HOME": "/root/.cache/huggingface",
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "PYTORCH_NVML_BASED_CUDA_CHECK": "0",
        }
    )
)


@app.cls(
    image=image,
    gpu=["L40S", "A100-40GB"],
    secrets=[dotenv_secret],
    volumes={"/root/.cache/huggingface": hf_cache_vol},
    timeout=900,
    memory=65536,
    scaledown_window=150,
    max_containers=1,
)
class Krea2Ref2ImgWorker:
    def __init__(self, storage):
        self.storage = storage

    @modal.enter()
    def load(self):
        print("[INIT] loading model krea/Krea-2-Turbo", flush=True)
        t0 = time.time()
        import torch
        import torch.distributed as dist

        dist.is_available = lambda: False

        # Qwen3-VL rope monkey-patch
        import transformers.models.qwen3_vl.modeling_qwen3_vl as _q3vl_modeling

        _orig_q3vl_rope_init = _q3vl_modeling.Qwen3VLTextRotaryEmbedding.__init__

        def _q3vl_safe_rope_init(self_rope, config, device=None):
            if getattr(config, "rope_scaling", None) is None:
                config.rope_scaling = {
                    "rope_type": "default",
                    "mrope_section": [24, 20, 20],
                }
            _orig_q3vl_rope_init(self_rope, config, device)

        _q3vl_modeling.Qwen3VLTextRotaryEmbedding.__init__ = _q3vl_safe_rope_init

        from pathlib import Path
        from diffusers import DiffusionPipeline
        from huggingface_hub import snapshot_download
        from transformers import AutoTokenizer

        self.torch = torch

        runtime_dir = Path(
            snapshot_download(
                REID_REPO,
                allow_patterns=[
                    "pipeline.py",
                    "face_crop.py",
                    "models/*.onnx",
                    "krea2_reid_rank32.safetensors",
                ],
            )
        )
        self.runtime_dir = runtime_dir

        token = os.environ.get("HF_TOKEN") or None

        self.tokenizer = AutoTokenizer.from_pretrained(
            MODEL_REPO,
            subfolder="tokenizer",
            token=token,
            trust_remote_code=True,
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

        self.pipe = DiffusionPipeline.from_pretrained(
            MODEL_REPO,
            custom_pipeline=str(runtime_dir),
            torch_dtype=torch.bfloat16,
            token=token,
            trust_remote_code=True,
            tokenizer=None,
        )
        self.pipe.tokenizer = self.tokenizer
        self.pipe.load_lora_weights(
            runtime_dir,
            weight_name="krea2_reid_rank32.safetensors",
            adapter_name="reid",
        )
        self.pipe.set_adapters(["reid"], weights=[1.0])
        self.pipe.enable_model_cpu_offload()
        print(f"[INIT] model loaded in {time.time() - t0:.1f}s", flush=True)

    def _decode_image(self, base64_str: str):
        import base64
        import io
        from PIL import Image

        img = Image.open(io.BytesIO(base64.b64decode(base64_str)))
        return img.convert("RGB")

    def _face_crop(self, img, margin: float = 0.4):
        import cv2
        import numpy as np
        from PIL import Image

        onnx = any(self.runtime_dir.glob("models/*face*.onnx"))
        if not onnx:
            return img

        bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        detector = cv2.FaceDetectorYN_create(
            str(next(self.runtime_dir.glob("models/*face*.onnx"))),
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

    @modal.method()
    def generate(
        self,
        prompt: str,
        reference_image: Optional[str] = None,
        height: int = 768,
        width: int = 768,
        num_inference_steps: int = 8,
        guidance_scale: float = 0.0,
        seed: Optional[int] = None,
        lora_scale: float = 1.0,
        face_crop: bool = True,
    ) -> dict:
        import uuid
        import boto3
        t_req = time.time()
        print(f"[REQ] prompt={prompt[:40]}  seed={seed}  files={1 if reference_image else 0}", flush=True)

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

        self.pipe.set_adapters(["reid"], weights=[req.lora_scale])

        base_kwargs = {
            "prompt": req.prompt,
            "width": req.width,
            "height": req.height,
            "num_inference_steps": req.num_inference_steps,
            "guidance_scale": req.guidance_scale,
        }
        if req.seed is not None:
            base_kwargs["generator"] = self.torch.Generator(device="cpu").manual_seed(req.seed)

        print(f"[GEN] starting inference prompt={prompt[:40]}", flush=True)
        t_gen = time.time()

        if req.reference_image:
            ref = self._decode_image(req.reference_image)
            if req.face_crop:
                ref = self._face_crop(ref)
            result = self.pipe(
                **base_kwargs,
                image=ref,
                reference_max_pixels=384 * 384,
                vl_image_max_pixels=384 * 384,
                encode_reference_in_prompt=True,
                kv_cache=True,
            )
        else:
            result = self.pipe(**base_kwargs)

        print(f"[GEN] inference done in {time.time() - t_gen:.1f}s  shape={image.size[0] if hasattr(image, 'size') else '?'}x{image.size[1] if hasattr(image, 'size') else '?'}", flush=True)
        image = result.images[0]
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        file_bytes = buffer.getvalue()

        key = f"krea2_{uuid.uuid4()}.png"
        self.storage.put(key, file_bytes)
        presigned_url = self.storage.presigned_url(key)
        print(f"[R2] uploaded key={key} url={presigned_url[:60]}", flush=True)

        print(f"[OK] completed in {time.time() - t_req:.1f}s", flush=True)
        return {"artifact": {"presigned_url": presigned_url}}

    @modal.fastapi_endpoint(method="POST")
    def generate_web(self, item: Krea2Ref2ImgInput) -> dict:
        try:
            return self.generate.local(
            prompt=item.prompt,
            reference_image=item.reference_image,
            height=item.height,
            width=item.width,
            num_inference_steps=item.num_inference_steps,
            guidance_scale=item.guidance_scale,
            seed=item.seed,
            lora_scale=item.lora_scale,
            face_crop=item.face_crop,
        )
        except Exception as e:
            print(f"[ERR] {type(e).__name__}: {e}", flush=True)
            raise
