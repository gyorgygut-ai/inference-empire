import base64
import io
import os
import uuid
from pathlib import Path

import boto3
from PIL import Image as PILImage

from beam import Image, QueueDepthAutoscaler, Volume, task_queue
from pydantic import BaseModel, ConfigDict, Field


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
        "transformers>=4.57,<5",
        "pillow",
        "accelerate",
        "diffusers",
        "sdnq",
        "boto3",
    ])
    .with_envs({
        "HF_HOME": CACHE_PATH,
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
    })
)

_MAX_WIDTH = 2560
_MAX_HEIGHT = 2560


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


def _prepare_image(base64_str: str):
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


def _run_generate(
    pipe,
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
        pipe_kwargs["generator"] = pipe.torch.Generator(device="cuda").manual_seed(req.seed)

    images = []
    if req.input_image:
        images.append(_prepare_image(req.input_image))
    for ref in req.reference_images or []:
        images.append(_prepare_image(ref))
    if images:
        pipe_kwargs["image"] = images

    image = pipe(**pipe_kwargs).images[0]

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


@task_queue(
    name="flux2-klein9b-worker",
    cpu=4,
    memory="32Gi",
    gpu="RTX4090",
    image=image,
    on_start=load_pipeline,
    volumes=[Volume(name="hf-cache", mount_path=CACHE_PATH)],
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=1800,
    checkpoint_enabled=True,
    timeout=3600,
    secrets=["HF_TOKEN", "R2_ACCESS_KEY", "R2_SECRET_KEY"],
)
def generate(context, prompt: str,
             height: int = 512, width: int = 512,
             guidance_scale: float = 1.0, num_inference_steps: int = 4,
             seed: int | None = None, input_image: str | None = None,
             reference_images: list[str] = []) -> dict:
    pipe = context.on_start_value
    return _run_generate(
        pipe,
        prompt=prompt,
        height=height,
        width=width,
        guidance_scale=guidance_scale,
        num_inference_steps=num_inference_steps,
        seed=seed,
        input_image=input_image,
        reference_images=reference_images,
    )
