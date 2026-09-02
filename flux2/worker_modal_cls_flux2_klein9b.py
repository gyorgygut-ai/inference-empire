import base64
import io
import os
import uuid
from pathlib import Path

import boto3
import modal
from pydantic import BaseModel, ConfigDict, Field

app = modal.App("flux2-klein9b-worker")


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
    @modal.enter()
    def load(self):
        self.pipe = load_pipeline()

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

        image = self.pipe(**pipe_kwargs).images[0]

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        file_bytes = buffer.getvalue()

        s3 = boto3.client("s3", endpoint_url=os.environ["R2_ENDPOINT"],
            aws_access_key_id=os.environ["R2_ACCESS_KEY"],
            aws_secret_access_key=os.environ["R2_SECRET_KEY"])
        key = f"flux2_{uuid.uuid4()}.png"
        bucket = os.environ.get("R2_BUCKET", "generated-media")
        s3.put_object(Bucket=bucket, Key=key, Body=file_bytes, ContentType="image/png")

        return {"artifact": {"presigned_url": s3.generate_presigned_url("get_object",
            Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600)}}

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

    @modal.fastapi_endpoint(method="POST")
    def generate_web(self, item: Flux2Klein9bInput) -> dict:
        return self.generate.remote(
            prompt=item.prompt,
            height=item.height,
            width=item.width,
            guidance_scale=item.guidance_scale,
            num_inference_steps=item.num_inference_steps,
            seed=item.seed,
            input_image=item.input_image,
            reference_images=item.reference_images,
        )