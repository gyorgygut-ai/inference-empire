import os
import uuid

import boto3
from runpod_flash import Endpoint, GpuGroup




@Endpoint(
    name="krea2-ref2img-worker",
    gpu=[GpuGroup.AMPERE_48, GpuGroup.ADA_48_PRO],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env={
        "HF_HOME": "/runpod-volume/huggingface-cache",
        "HF_TOKEN": os.environ.get("HF_TOKEN", ""),
        "PYTORCH_NVML_BASED_CUDA_CHECK": "0",
        "R2_BUCKET": os.environ.get("R2_BUCKET", "generated-media"),
        "R2_ENDPOINT": os.environ.get("R2_ENDPOINT", ""),
        "R2_ACCESS_KEY": os.environ.get("R2_ACCESS_KEY", ""),
        "R2_SECRET_KEY": os.environ.get("R2_SECRET_KEY", ""),
    },
    dependencies=[
        "torch==2.9.1",
        "diffusers",
        "transformers>=4.57,<5",
        "accelerate",
        "safetensors",
        "huggingface_hub",
        "pillow",
        "protobuf",
        "opencv-python-headless",
        "peft",
        "boto3",
    ],
)
class Krea2Ref2ImgWorker:
    # --- BEGIN CONTRACT: krea2_ref2img (generated; run make gen-contracts) ---
    from pydantic import BaseModel

    class Input(BaseModel):
        from typing import Literal as _Literal, Optional as _Optional
        from pydantic import BaseModel as _BaseModel, ConfigDict as _ConfigDict, Field as _Field

        model_config = _ConfigDict(title='Krea2Ref2ImgInput')
        prompt: str
        reference_image: _Optional[str] = _Field(default=None)
        height: int = _Field(default=768)
        width: int = _Field(default=768)
        num_inference_steps: int = _Field(default=8)
        guidance_scale: float = _Field(default=0.0)
        seed: _Optional[int] = _Field(default=None)
        lora_scale: float = _Field(default=1.0)
        face_crop: bool = _Field(default=True)
    # --- END CONTRACT: krea2_ref2img ---


















    def __init__(self):
        import torch.distributed as dist

        dist.is_available = lambda: False

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

        import os
        from pathlib import Path

        import torch
        from diffusers import DiffusionPipeline
        from huggingface_hub import snapshot_download
        from transformers import AutoTokenizer

        self.torch = torch

        runtime_dir = Path(
            snapshot_download(
                "yijunwang2/krea2-reid",
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

        # Krea-2-Turbo's tokenizer/ folder ships only tokenizer.json (no
        # vocab.json), and its tokenizer_config.json stores `extra_special_tokens`
        # as a raw list. Both break transformers 4.57.x:
        #   - the slow Qwen2Tokenizer declared in model_index.json needs
        #     vocab.json -> open(None) -> TypeError
        #   - the fast path passes the list straight into the constructor, where
        #     _set_model_specific_special_tokens calls .keys() -> AttributeError
        self.tokenizer = AutoTokenizer.from_pretrained(
            "krea/Krea-2-Turbo",
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

        # trust_remote_code is required by diffusers 0.39 to execute the custom
        # pipeline.py (the official example predates the strict check).
        self.pipe = DiffusionPipeline.from_pretrained(
            "krea/Krea-2-Turbo",
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

    def _decode_image(self, base64_str: str):
        import base64
        import io

        from PIL import Image

        img = Image.open(io.BytesIO(base64.b64decode(base64_str)))
        return img.convert("RGB")

    def _face_crop(self, img, margin: float = 0.4):
        import cv2
        import numpy as np

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

        from PIL import Image

        return Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))

    def generate(
        self,
        prompt: str,
        reference_image: str | None = None,
        height: int = 768,
        width: int = 768,
        num_inference_steps: int = 8,
        guidance_scale: float = 0.0,
        seed: int | None = None,
        lora_scale: float = 1.0,
        face_crop: bool = True,
    ) -> dict:
        import base64
        import io

        req = self.Input(
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
            base_kwargs["generator"] = self.torch.Generator(device="cpu").manual_seed(
                req.seed
            )

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

        image = result.images[0]
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        file_bytes = buffer.getvalue()

        bucket = os.environ.get("R2_BUCKET", "generated-media")
        endpoint = os.environ["R2_ENDPOINT"]
        access_key = os.environ["R2_ACCESS_KEY"]
        secret_key = os.environ["R2_SECRET_KEY"]

        key = f"krea2_{uuid.uuid4()}.png"
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        s3.put_object(Bucket=bucket, Key=key, Body=file_bytes, ContentType="image/png")
        presigned_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=3600,
        )

        return {"artifact": {"presigned_url": presigned_url}}
