"""Shared business logic for minimax-h3-comfy (ComfyUI backend). No platform imports."""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from workers.services.storage.storage import Storage

MODEL_FILES = {
    "unet_name": "minimax_h3_fl2va_pruned_int8_convrot.safetensors",
    "clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
    "vae_video_name": "minimax_h3_video_vae_fp16.safetensors",
    "vae_audio_name": "minimax_h3_audio_vae_fp32.safetensors",
}
FPS = 24

# Single source of truth for ALL provider image pip deps (flash; modal/beam
# use a pinned registry image instead). Worker files must reference this
# list, never inline their own pins.
# Pre-deploy gate: uv run python -c "from workers.h3._shared_minimax_h3_comfy import IMAGE_PIP_DEPS; print('\n'.join(IMAGE_PIP_DEPS))" | uv pip compile --python-version 3.11 -
IMAGE_PIP_DEPS: list[str] = [
    "boto3==1.43.83",
    "pydantic==2.13.5",
]


def apply_torch_shims() -> None:
    """Patch torch runtime quirks once (remote containers)."""
    import torch.distributed as dist

    try:
        def _dist_unavailable() -> bool:
            return False

        setattr(dist, "is_available", _dist_unavailable)
    except Exception:  # noqa: BLE001, S110
        pass


def _load_dotenv() -> None:
    path = Path(__file__).parent.parent / ".env"
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


class MiniMaxH3ComfyInput(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3ComfyInput")
    prompt: str
    width: int = Field(default=1344)
    height: int = Field(default=768)
    length: int = Field(default=124)
    steps: int = Field(default=20)
    seed: int | None = Field(default=None)
    first_frame: str | None = Field(default=None)
    last_frame: str | None = Field(default=None)

class Artifact(BaseModel):
    model_config = ConfigDict(title="Artifact")
    presigned_url: str

class MiniMaxH3ComfyOutput(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3ComfyOutput")
    artifact: Artifact
    video: str

def build_workflow(req: MiniMaxH3ComfyInput) -> dict:
    workflow = {
        "unet": {"class_type": "UNETLoader", "inputs": {"unet_name": MODEL_FILES["unet_name"], "weight_dtype": "default"}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": MODEL_FILES["clip_name"], "type": "minimax", "device": "default"}},
        "vae_video": {"class_type": "VAELoader", "inputs": {"vae_name": MODEL_FILES["vae_video_name"]}},
        "vae_audio": {"class_type": "VAELoader", "inputs": {"vae_name": MODEL_FILES["vae_audio_name"]}},
        "cond": {"class_type": "MiniMaxH3ImageToVideo", "inputs": {
            "clip": ["clip", 0], "vae": ["vae_video", 0],
            "prompt": req.prompt, "width": req.width, "height": req.height, "length": req.length}},
        "noise": {"class_type": "RandomNoise", "inputs": {"noise_seed": req.seed if req.seed is not None else 42}},
        "guider": {"class_type": "BasicGuider", "inputs": {"model": ["unet", 0], "conditioning": ["cond", 0]}},
        "sampler_select": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
        "sigmas": {"class_type": "BasicScheduler", "inputs": {"model": ["unet", 0], "scheduler": "simple", "steps": req.steps, "denoise": 1.0}},
        "sample": {"class_type": "SamplerCustomAdvanced", "inputs": {
            "noise": ["noise", 0], "guider": ["guider", 0], "sampler": ["sampler_select", 0],
            "sigmas": ["sigmas", 0], "latent_image": ["cond", 1]}},
        "decode_video": {"class_type": "VAEDecode", "inputs": {"samples": ["sample", 0], "vae": ["vae_video", 0]}},
        "decode_audio": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["sample", 0], "vae": ["vae_audio", 0]}},
        "video": {"class_type": "CreateVideo", "inputs": {"images": ["decode_video", 0], "fps": FPS, "audio": ["decode_audio", 0]}},
        "save": {"class_type": "SaveVideo", "inputs": {"video": ["video", 0], "filename_prefix": "video/MiniMax_H3", "format": "auto", "codec": "auto"}},
    }
    if req.first_frame:
        workflow["load_first"] = {"class_type": "LoadImage", "inputs": {"image": "first_frame.png"}}
        workflow["cond"]["inputs"]["first_frame"] = ["load_first", 0]
    if req.last_frame:
        workflow["load_last"] = {"class_type": "LoadImage", "inputs": {"image": "last_frame.png"}}
        workflow["cond"]["inputs"]["last_frame"] = ["load_last", 0]
    return workflow

def build_images(req: MiniMaxH3ComfyInput) -> list[dict]:
    images = []
    if req.first_frame:
        images.append({"name": "first_frame.png", "image": f"data:image/png;base64,{req.first_frame}"})
    if req.last_frame:
        images.append({"name": "last_frame.png", "image": f"data:image/png;base64,{req.last_frame}"})
    return images

def build_payload(req: MiniMaxH3ComfyInput) -> dict:
    payload = {"workflow": build_workflow(req)}
    images = build_images(req)
    if images:
        payload["images"] = images
    return payload

def parse_output(output) -> tuple:
    """Returns (video_bytes, data). Raises RuntimeError on malformed output."""
    import base64

    if not isinstance(output, dict):
        raise TypeError(f"unexpected output: {output!r}")
    out_images = output.get("images") or []
    if not out_images:
        raise RuntimeError(f"no video in output: {output}")
    data = out_images[0].get("data")
    if not data:
        raise RuntimeError(f"no data in image result: {out_images[0]}")
    return base64.b64decode(data), data

def upload_result(storage: Storage, video_bytes: bytes, data: str, prefix: str = "minimax_comfy") -> MiniMaxH3ComfyOutput:
    key = f"{prefix}_{uuid.uuid4()}.mp4"
    storage.put(key, video_bytes)
    presigned_url = storage.presigned_url(key)
    return MiniMaxH3ComfyOutput(artifact=Artifact(presigned_url=presigned_url), video=data)

def run_comfy_endpoint(endpoint, payload, timeout: int = 1800):
    """Submit payload to a ComfyUI flash endpoint, tolerating a running loop."""
    import asyncio
    import concurrent.futures

    async def _run():
        return await endpoint.runsync(payload, timeout=timeout)

    try:
        return asyncio.run(_run())
    except RuntimeError:
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(lambda: asyncio.run(_run())).result()

def _run_local(comfy_base_url: str, req: MiniMaxH3ComfyInput) -> tuple:
    """Submit + 600s poll + fetch. Returns (video_bytes, data)."""
    import base64
    import time

    import requests

    print(f"[REQ] prompt={req.prompt[:40]}", flush=True)
    payload = build_payload(req)

    print(f"[GEN] starting ComfyUI job prompt={req.prompt[:40]}", flush=True)
    t_gen = time.time()
    r = requests.post(f"{comfy_base_url}/prompt", json=payload, timeout=30)
    r.raise_for_status()
    prompt_id = r.json()["prompt_id"]

    for attempt in range(600):
        try:
            r = requests.get(f"{comfy_base_url}/history/{prompt_id}", timeout=10)
            history = r.json()
            if prompt_id in history:
                outputs = history[prompt_id]["outputs"]
                save_node = outputs.get("save", {})
                video_info = (save_node.get("videos") or save_node.get("gifs") or [None])[0]
                if video_info:
                    break
        except (requests.ConnectionError, requests.Timeout, ValueError) as e:
            print(
                f"[COMFY] poll {attempt + 1}/600 transient error: {type(e).__name__}: {e}",
                flush=True,
            )
        time.sleep(1)
    else:
        raise RuntimeError(f"ComfyUI job {prompt_id} did not complete within 600s")

    print(f"[GEN] ComfyUI job done in {time.time() - t_gen:.1f}s", flush=True)
    video_url = (
        f"{comfy_base_url}/view?filename={video_info['filename']}"
        f"&subfolder={video_info.get('subfolder', '')}&type={video_info.get('type', 'output')}"
    )
    video_bytes = requests.get(video_url, timeout=60).content
    data = base64.b64encode(video_bytes).decode("ascii")

    return video_bytes, data

def _run_flash(endpoint, req: MiniMaxH3ComfyInput) -> tuple:
    """Submit via flash endpoint. Returns (video_bytes, data)."""
    import time

    print(f"[REQ] prompt={req.prompt[:40]}", flush=True)
    payload = build_payload(req)

    print(f"[GEN] starting ComfyUI job prompt={req.prompt[:40]}", flush=True)
    t_gen = time.time()
    job = run_comfy_endpoint(endpoint, payload)
    print(f"[GEN] ComfyUI job done in {time.time() - t_gen:.1f}s", flush=True)

    if getattr(job, "error", None):
        raise RuntimeError(f"job failed: {job.error}")

    output = getattr(job, "output", None) or job
    return parse_output(output)

def do_inference(backend, storage: Storage, req: MiniMaxH3ComfyInput) -> MiniMaxH3ComfyOutput:
    """Local (base_url str) and flash (endpoint) paths converge here. Testable via DI."""
    import time

    t_req = time.time()
    if isinstance(backend, str):
        video_bytes, data = _run_local(backend, req)
    else:
        video_bytes, data = _run_flash(backend, req)

    result = upload_result(storage, video_bytes, data, prefix="minimax_comfy")
    print(f"[R2] uploaded key={result.artifact.presigned_url[:60]}", flush=True)

    print(f"[OK] completed in {time.time() - t_req:.1f}s", flush=True)
    return result
