import os
import time
import uuid

import boto3
from runpod_flash import Endpoint, GpuGroup


@Endpoint(
    name="flux2-klein9b-worker",
    gpu=[
        GpuGroup.AMPERE_16,
    ],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env={
        "SDNQ_USE_TRITON_MM": "0",
        "HF_TOKEN": os.environ.get("HF_TOKEN", ""),
        "HF_HOME": "/runpod-volume/huggingface-cache",
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
        "sdnq",
        "huggingface_hub",
        "pillow",
        "boto3",
    ],
)
class FluxKleinWorker:
    # --- BEGIN CONTRACT: flux2_klein9b (generated; run make gen-contracts) ---
    from pydantic import BaseModel

    class Input(BaseModel):
        from typing import Literal as _Literal, Optional as _Optional
        from pydantic import BaseModel as _BaseModel, ConfigDict as _ConfigDict, Field as _Field

        model_config = _ConfigDict(title='Flux2Klein9bInput')
        prompt: str
        height: int = _Field(default=512)
        width: int = _Field(default=512)
        guidance_scale: float = _Field(default=1.0)
        num_inference_steps: int = _Field(default=4)
        seed: _Optional[int] = _Field(default=None)
        input_image: _Optional[str] = _Field(default=None)
        reference_images: list[str] = _Field(default=[])
    # --- END CONTRACT: flux2_klein9b ---




















    def __init__(self, pipe=None, storage=None):
        self.storage = storage

        import torch.distributed as dist
        dist.is_available = lambda: False

        import base64
        import io
        import os
        import diffusers
        import torch
        from PIL import Image
        from sdnq import SDNQConfig

        self.torch = torch
        self.base64 = base64
        self.io = io
        self.Image = Image

        # If pipe injected via DI (for testing), use it; otherwise load real model
        if pipe is not None:
            self.pipe = pipe
        else:
            MODEL_ID = "Disty0/FLUX.2-klein-9B-SDNQ-4bit-dynamic-svd-r32"
            print("[INIT] loading model Disty0/FLUX.2-klein-9B-SDNQ-4bit-dynamic-svd-r32", flush=True)
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

            self.pipe = pipe
            print(f"[INIT] model loaded in {time.time() - t0:.1f}s", flush=True)

    def _prepare_image(self, base64_str: str):
        img = self.Image.open(self.io.BytesIO(self.base64.b64decode(base64_str)))
        img = img.convert("RGB")
        w, h = img.size
        w = min(w - (w % 16), 2560)
        h = min(h - (h % 16), 2560)
        if w != img.size[0] or h != img.size[1]:
            img = img.resize((w, h))
        return img

    def _run_generate(
        self,
        prompt: str,
        height: int = 512,
        width: int = 512,
        guidance_scale: float = 1.0,
        num_inference_steps: int = 4,
        seed: int | None = None,
        input_image: str | None = None,
        reference_images: list[str] = [],
    ) -> dict:
        """Pure sync generate logic - testable via DI. Tests call this directly."""
        t_req = time.time()
        n_refs = (1 if input_image else 0) + len(reference_images or [])
        print(f"[REQ] prompt={prompt[:40]}  seed={seed}  files={n_refs}", flush=True)

        req = self.Input(
            prompt=prompt,
            height=height,
            width=width,
            guidance_scale=guidance_scale,
            num_inference_steps=num_inference_steps,
            seed=seed,
            input_image=input_image,
            reference_images=reference_images,
        )

        pipe_kwargs = {
            "prompt": req.prompt,
            "height": req.height,
            "width": req.width,
            "guidance_scale": req.guidance_scale,
            "num_inference_steps": req.num_inference_steps,
        }

        if req.seed is not None:
            pipe_kwargs["generator"] = self.torch.Generator(device="cuda").manual_seed(
                req.seed
            )

        images = []
        if req.input_image:
            images.append(self._prepare_image(req.input_image))
        for ref in req.reference_images or []:
            images.append(self._prepare_image(ref))
        if images:
            pipe_kwargs["image"] = images

        print(f"[GEN] starting inference prompt={prompt[:40]}", flush=True)
        t_gen = time.time()
        image = self.pipe(**pipe_kwargs).images[0]
        print(f"[GEN] inference done in {time.time() - t_gen:.1f}s  shape={image.size[0]}x{image.size[1]}", flush=True)

        buffer = self.io.BytesIO()
        image.save(buffer, format="PNG")
        file_bytes = buffer.getvalue()

        key = f"flux2_{uuid.uuid4()}.png"
        self.storage.put(key, file_bytes)
        presigned_url = self.storage.presigned_url(key)
        print(f"[R2] uploaded key={key} url={presigned_url[:60]}", flush=True)

        print(f"[OK] completed in {time.time() - t_req:.1f}s", flush=True)
        return {"artifact": {"presigned_url": presigned_url}}

    def generate(
        self,
        prompt: str,
        height: int = 512,
        width: int = 512,
        guidance_scale: float = 1.0,
        num_inference_steps: int = 4,
        seed: int | None = None,
        input_image: str | None = None,
        reference_images: list[str] = [],
    ) -> dict:
        """Public API - delegates to _run_generate. Tests call _run_generate directly."""
        try:
            return self._run_generate(
                prompt=prompt,
                height=height,
                width=width,
                guidance_scale=guidance_scale,
                num_inference_steps=num_inference_steps,
                seed=seed,
                input_image=input_image,
                reference_images=reference_images,
            )
        except Exception as e:
            print(f"[ERR] {type(e).__name__}: {e}", flush=True)
            raise