import base64
import io
import os
import time
import uuid
from pathlib import Path

import boto3
import modal
from pydantic import BaseModel, ConfigDict, Field

app = modal.App("flux2-klein9b-worker")

START_TIME = time.time()


@app.local_entrypoint()
def main(
    prompt: str = "a cat sitting on a rocket ship",
    height: int = 512,
    width: int = 512,
    num_inference_steps: int = 4,
    seed: int = -1,
):
    import json

    worker = FluxKleinWorker()
    result = worker.generate.remote(
        prompt=prompt,
        height=height,
        width=width,
        num_inference_steps=num_inference_steps,
        seed=seed if seed >= 0 else None,
    )
    print(json.dumps(result, indent=2))

dotenv_secret = modal.Secret.from_dotenv(str(Path(__file__).parent.parent / ".env"))
hf_cache_vol = modal.Volume.from_name("hf-cache", create_if_missing=True)


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


image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg", "libgl1", "libglib2.0-0")
    .pip_install(
        "torch==2.9.1",
        "transformers>=5.0,<6",
        "accelerate==1.14.0",
        "diffusers==0.40.0",
        "sdnq==0.2.6",
        "boto3==1.43.83",
        "pillow==12.3.0",
        "fastapi[standard]==0.141.1",
        "hf_transfer==0.1.9",
    )
    .env({
        "HF_HOME": "/root/.cache/huggingface",
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
    })
)


def load_pipeline():
    import torch
    import torch.distributed as dist

    try:
        dist.is_available = lambda: False
    except Exception:
        pass

    import diffusers

    token = os.environ.get("HF_TOKEN")

    pipe = diffusers.Flux2KleinPipeline.from_pretrained(
        "Disty0/FLUX.2-klein-9B-SDNQ-4bit-dynamic-svd-r32",
        torch_dtype=torch.bfloat16,
        token=token,
    )
    pipe.to("cuda")
    return pipe


@app.cls(
    image=image,
    gpu="L4",
    secrets=[dotenv_secret],
    volumes={"/root/.cache/huggingface": hf_cache_vol},
    timeout=600,
    memory=32768,
    scaledown_window=150,
    max_containers=1,
)
class FluxKleinWorker:
    def __init__(self, storage):
        self.storage = storage

    @modal.enter()
    def load(self):
        print("[INIT] loading model Disty0/FLUX.2-klein-9B-SDNQ-4bit-dynamic-svd-r32", flush=True)
        t0 = time.time()
        self.pipe = load_pipeline()
        print(f"[INIT] model loaded in {time.time() - t0:.1f}s", flush=True)

    def _prepare_image(self, base64_str: str):
        from PIL import Image

        img = Image.open(io.BytesIO(base64.b64decode(base64_str))).convert("RGB")
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

        req = Flux2Klein9bInput(
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
            pipe_kwargs["generator"] = self.pipe.torch.Generator(device="cuda").manual_seed(req.seed)

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

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        file_bytes = buffer.getvalue()

        key = f"flux2_{uuid.uuid4()}.png"
        self.storage.put(key, file_bytes)
        url = self.storage.presigned_url(key)
        print(f"[R2] uploaded key={key} url={url[:60]}", flush=True)

        print(f"[OK] completed in {time.time() - t_req:.1f}s", flush=True)
        return {"artifact": {"presigned_url": url}}

    @modal.method()
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

    @modal.fastapi_endpoint(method="POST")
    def generate_web(self, item: Flux2Klein9bInput) -> dict:
        try:
            return self._run_generate(
                prompt=item.prompt,
                height=item.height,
                width=item.width,
                guidance_scale=item.guidance_scale,
                num_inference_steps=item.num_inference_steps,
                seed=item.seed,
                input_image=item.input_image,
                reference_images=item.reference_images,
            )
        except Exception as e:
            print(f"[ERR] {type(e).__name__}: {e}", flush=True)
            raise