import base64
import io
import os
import time
import uuid
from pathlib import Path

import boto3
from PIL import Image as PILImage

from beam import Image, QueueDepthAutoscaler, Volume, task_queue
from pydantic import BaseModel, ConfigDict, Field


START = time.time()


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
        "transformers>=5.0,<6",
        "accelerate==1.14.0",
        "diffusers==0.40.0",
        "sdnq==0.2.6",
        "pillow==12.3.0",
        "boto3==1.43.83",
    ])
    .with_envs({
        "HF_HOME": CACHE_PATH,
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
        "R2_ENDPOINT": "https://29b2f092b2dbc0b63f48f491ddc177ee.r2.cloudflarestorage.com",
        "R2_BUCKET": "generated-media",
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

    print("[INIT] loading model Disty0/FLUX.2-klein-9B-SDNQ-4bit-dynamic-svd-r32", flush=True)
    t0 = time.time()

    import diffusers

    token = os.environ.get("HF_TOKEN")

    pipe = diffusers.Flux2KleinPipeline.from_pretrained(
        "Disty0/FLUX.2-klein-9B-SDNQ-4bit-dynamic-svd-r32",
        torch_dtype=torch.bfloat16,
        token=token,
    )
    pipe.to("cuda")
    print(f"[INIT] model loaded in {time.time() - t0:.1f}s", flush=True)
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
    n_refs = (1 if input_image else 0) + len(reference_images or [])
    print(f"[REQ] prompt={prompt[:40]}  seed={seed}  files={n_refs}", flush=True)
    t0 = time.time()

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

    print(f"[GEN] starting inference prompt={prompt[:40]}", flush=True)
    gen_start = time.time()
    image = pipe(**pipe_kwargs).images[0]
    print(f"[GEN] inference done in {time.time() - gen_start:.1f}s  shape={image.size[0]}x{image.size[1]}", flush=True)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    file_bytes = buffer.getvalue()

    key = f"flux2_{uuid.uuid4()}.png"
    storage.put(key, file_bytes)
    url = storage.presigned_url(key)
    print(f"[R2] uploaded key={key} url={url[:60]}", flush=True)

    print(f"[OK] completed in {time.time() - t0:.1f}s", flush=True)
    return {"artifact": {"presigned_url": url}}


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
    secrets=["HF_TOKEN", "R2_ACCESS_KEY", "R2_SECRET_KEY", "R2_ENDPOINT"],
)
def generate(context, prompt: str,
             height: int = 512, width: int = 512,
             guidance_scale: float = 1.0, num_inference_steps: int = 4,
             seed: int | None = None, input_image: str | None = None,
             reference_images: list[str] = [], storage=None) -> dict:
    pipe = context.on_start_value
    try:
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
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise
