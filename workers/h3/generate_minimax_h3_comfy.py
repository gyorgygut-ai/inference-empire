"""Shared business logic for minimax-h3-comfy (ComfyUI backend). No platform imports."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

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


class MiniMaxH3ComfyInput(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3ComfyInput")
    prompt: str
    width: int = Field(default=1344)
    height: int = Field(default=768)
    length: int = Field(default=124)
    steps: int = Field(default=20)
    seed: Optional[int] = Field(default=None)
    first_frame: Optional[str] = Field(default=None)
    last_frame: Optional[str] = Field(default=None)


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
        raise RuntimeError(f"unexpected output: {output!r}")
    out_images = output.get("images") or []
    if not out_images:
        raise RuntimeError(f"no video in output: {output}")
    data = out_images[0].get("data")
    if not data:
        raise RuntimeError(f"no data in image result: {out_images[0]}")
    return base64.b64decode(data), data


def upload_result(storage: Storage, video_bytes: bytes, data: str, prefix: str = "minimax_comfy") -> MiniMaxH3ComfyOutput:
    if storage is None:
        raise ValueError("storage is required")
    key = f"{prefix}_{uuid.uuid4()}.mp4"
    storage.put(key, video_bytes)
    presigned_url = storage.presigned_url(key)
    return MiniMaxH3ComfyOutput(artifact=Artifact(presigned_url=presigned_url), video=data)
