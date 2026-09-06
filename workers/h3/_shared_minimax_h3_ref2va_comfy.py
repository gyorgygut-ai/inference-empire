"""Shared business logic for minimax-h3-ref2va-comfy (ComfyUI backend). No platform imports."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from workers.h3._shared_minimax_h3_comfy import run_comfy_endpoint

if TYPE_CHECKING:
    from workers.services.storage.storage import Storage

MODEL_FILES = {
    "unet_name": "minimax_h3_ref2va_pruned_int8_convrot.safetensors",
    "clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
    "vae_video_name": "minimax_h3_video_vae_fp16.safetensors",
    "vae_audio_name": "minimax_h3_audio_vae_fp32.safetensors",
}
FPS = 24

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
_MAX_REF_IMAGES = 9
_MAX_REF_VIDEOS = 3
_MAX_REF_AUDIOS = 3
_MAX_TOTAL_FILES = 12

class MiniMaxH3Ref2VAComfyInput(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3Ref2VAComfyInput")
    prompt: str = Field(
        description="Prompt describing the target shot; reference inputs by tag in connection order, e.g. <Picture 1>, <Video 1>, <Audio 1>."
    )
    ref_images: list[str] = Field(
        default=[], max_length=9, description="Up to 9 reference images as base64 data URLs."
    )
    ref_videos: list[str] = Field(
        default=[],
        max_length=3,
        description="Up to 3 reference video clips as base64 data URLs.",
    )
    ref_video_audios: list[str] = Field(
        default=[],
        max_length=3,
        description="Audio track paired with each reference video (index-aligned with ref_videos).",
    )
    ref_audios: list[str] = Field(
        default=[], max_length=3, description="Up to 3 standalone reference audio clips."
    )
    width: int = Field(default=1344)
    height: int = Field(default=768)
    length: int = Field(default=124)
    steps: int = Field(default=20)
    seed: int | None = Field(default=None)
    ref_image_size: Literal["match", "max"] = Field(default="match")
    scheduler: Literal["simple", "beta", "normal"] = Field(default="simple")

    @field_validator("ref_audios")
    @classmethod
    def _check_audio_not_alone(cls, v: list[str], info) -> list[str]:
        if v:
            has_visual = bool(info.data.get("ref_images")) or bool(info.data.get("ref_videos"))
            if not has_visual:
                raise ValueError(
                    "reference audio requires at least one reference image or video"
                )
        return v

class ValidatedRef2VAComfyInput(MiniMaxH3Ref2VAComfyInput):
    @field_validator("ref_images")
    @classmethod
    def _check_ref_images(cls, v: list[str]) -> list[str]:
        if len(v) > _MAX_REF_IMAGES:
            raise ValueError(f"too many reference images: {len(v)} (max {_MAX_REF_IMAGES})")
        return v

    @field_validator("ref_videos")
    @classmethod
    def _check_ref_videos(cls, v: list[str]) -> list[str]:
        if len(v) > _MAX_REF_VIDEOS:
            raise ValueError(f"too many reference videos: {len(v)} (max {_MAX_REF_VIDEOS})")
        return v

    @field_validator("ref_video_audios")
    @classmethod
    def _check_ref_video_audios(cls, v: list[str]) -> list[str]:
        if len(v) > _MAX_REF_VIDEOS:
            raise ValueError(
                f"too many reference video audio tracks: {len(v)} (max {_MAX_REF_VIDEOS})"
            )
        return v

    @field_validator("ref_audios")
    @classmethod
    def _check_ref_audios(cls, v: list[str]) -> list[str]:
        if len(v) > _MAX_REF_AUDIOS:
            raise ValueError(f"too many reference audio clips: {len(v)} (max {_MAX_REF_AUDIOS})")
        return v

    @field_validator("ref_video_audios")
    @classmethod
    def _check_video_audio_pairs(cls, v: list[str], info) -> list[str]:
        ref_videos = info.data.get("ref_videos") or []
        if len(v) > len(ref_videos):
            raise ValueError(
                f"{len(v)} reference video audio tracks for {len(ref_videos)} reference videos "
                "(ref_video_audios is index-aligned with ref_videos)"
            )
        return v

    @field_validator("ref_images", "ref_videos", "ref_video_audios", "ref_audios")
    @classmethod
    def _check_total_files(cls, v: list[str], info) -> list[str]:
        total = (
            len(v)
            + len(info.data.get("ref_images") or [])
            + len(info.data.get("ref_videos") or [])
            + len(info.data.get("ref_video_audios") or [])
            + len(info.data.get("ref_audios") or [])
        )
        if total > _MAX_TOTAL_FILES:
            raise ValueError(f"too many reference files in total: {total} (max {_MAX_TOTAL_FILES})")
        return v

    @field_validator("ref_audios")
    @classmethod
    def _check_audio_not_alone(cls, v: list[str], info) -> list[str]:
        if v:
            has_visual = bool(info.data.get("ref_images")) or bool(info.data.get("ref_videos"))
            if not has_visual:
                raise ValueError(
                    "reference audio requires at least one reference image or video"
                )
        return v

class Artifact(BaseModel):
    model_config = ConfigDict(title="Artifact")
    presigned_url: str

class MiniMaxH3Ref2VAComfyOutput(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3Ref2VAComfyOutput")
    artifact: Artifact
    video: str

def build_workflow(req: ValidatedRef2VAComfyInput) -> dict:
    workflow = {
        "unet": {"class_type": "UNETLoader", "inputs": {"unet_name": MODEL_FILES["unet_name"], "weight_dtype": "default"}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": MODEL_FILES["clip_name"], "type": "minimax", "device": "default"}},
        "vae_video": {"class_type": "VAELoader", "inputs": {"vae_name": MODEL_FILES["vae_video_name"]}},
        "vae_audio": {"class_type": "VAELoader", "inputs": {"vae_name": MODEL_FILES["vae_audio_name"]}},
        "cond": {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": {
            "clip": ["clip", 0], "vae": ["vae_video", 0], "audio_vae": ["vae_audio", 0],
            "prompt": req.prompt, "width": req.width, "height": req.height,
            "length": req.length, "ref_image_size": req.ref_image_size}},
        "noise": {"class_type": "RandomNoise", "inputs": {"noise_seed": req.seed if req.seed is not None else 42}},
        "guider": {"class_type": "BasicGuider", "inputs": {"model": ["unet", 0], "conditioning": ["cond", 0]}},
        "sampler_select": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
        "sigmas": {"class_type": "BasicScheduler", "inputs": {"model": ["unet", 0], "scheduler": req.scheduler, "steps": req.steps, "denoise": 1.0}},
        "sample": {"class_type": "SamplerCustomAdvanced", "inputs": {
            "noise": ["noise", 0], "guider": ["guider", 0], "sampler": ["sampler_select", 0],
            "sigmas": ["sigmas", 0], "latent_image": ["cond", 1]}},
        "decode_video": {"class_type": "VAEDecode", "inputs": {"samples": ["sample", 0], "vae": ["vae_video", 0]}},
        "decode_audio": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["sample", 0], "vae": ["vae_audio", 0]}},
        "video": {"class_type": "CreateVideo", "inputs": {"images": ["decode_video", 0], "fps": FPS, "audio": ["decode_audio", 0]}},
        "save": {"class_type": "SaveVideo", "inputs": {"video": ["video", 0], "filename_prefix": "video/MiniMax_H3_Ref2VA", "format": "auto", "codec": "auto"}},
    }

    for i, _ in enumerate(req.ref_images):
        node_name = f"load_ref_image_{i + 1}"
        workflow[node_name] = {
            "class_type": "LoadImage",
            "inputs": {"image": f"ref_image_{i + 1}.png"},
        }
        workflow["cond"]["inputs"][f"ref_image_{i + 1}"] = [node_name, 0]

    for i, _ in enumerate(req.ref_videos):
        node_name = f"load_ref_video_{i + 1}"
        inputs = {"video": f"ref_video_{i + 1}.mp4"}
        if i < len(req.ref_video_audios):
            inputs["audio"] = f"ref_video_audio_{i + 1}.mp3"
        workflow[node_name] = {
            "class_type": "LoadVideo",
            "inputs": inputs,
        }
        workflow["cond"]["inputs"][f"ref_video_{i + 1}"] = [node_name, 0]
        if i < len(req.ref_video_audios):
            workflow["cond"]["inputs"][f"ref_video_audio_{i + 1}"] = [node_name, 1]

    for i, _ in enumerate(req.ref_audios):
        node_name = f"load_ref_audio_{i + 1}"
        workflow[node_name] = {
            "class_type": "LoadAudio",
            "inputs": {"audio": f"ref_audio_{i + 1}.mp3"},
        }
        workflow["cond"]["inputs"][f"ref_audio_{i + 1}"] = [node_name, 0]

    return workflow

def build_images(req: ValidatedRef2VAComfyInput) -> list[dict]:
    images = []
    for i, img in enumerate(req.ref_images):
        images.append(
            {"name": f"ref_image_{i + 1}.png", "image": f"data:image/png;base64,{img}"}
        )
    for i, vid in enumerate(req.ref_videos):
        images.append(
            {"name": f"ref_video_{i + 1}.mp4", "image": f"data:video/mp4;base64,{vid}"}
        )
    for i, aud in enumerate(req.ref_video_audios):
        images.append(
            {"name": f"ref_video_audio_{i + 1}.mp3", "image": f"data:audio/mp3;base64,{aud}"}
        )
    for i, aud in enumerate(req.ref_audios):
        images.append(
            {"name": f"ref_audio_{i + 1}.mp3", "image": f"data:audio/mp3;base64,{aud}"}
        )
    return images

def build_payload(req: ValidatedRef2VAComfyInput) -> dict:
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

def upload_result(storage: Storage, video_bytes: bytes, data: str, prefix: str = "minimax_ref2va_comfy") -> MiniMaxH3Ref2VAComfyOutput:
    if storage is None:
        raise ValueError("storage is required")
    key = f"{prefix}_{uuid.uuid4()}.mp4"
    storage.put(key, video_bytes)
    presigned_url = storage.presigned_url(key)
    return MiniMaxH3Ref2VAComfyOutput(artifact=Artifact(presigned_url=presigned_url), video=data)

def _run_beam(comfy_base_url: str, req: ValidatedRef2VAComfyInput) -> tuple:
    """Submit + 600s poll + fetch. Returns (video_bytes, data)."""
    import base64
    import time

    import requests

    t_req = time.time()
    n_files = (
        len(req.ref_images)
        + len(req.ref_videos)
        + len(req.ref_video_audios)
        + len(req.ref_audios)
    )
    print(f"[REQ] prompt={req.prompt[:40]}  seed={req.seed}  files={n_files}", flush=True)

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

    print(f"[OK] submit/poll/fetch in {time.time() - t_req:.1f}s", flush=True)
    return video_bytes, data

def _run_flash(endpoint, req: ValidatedRef2VAComfyInput) -> tuple:
    """Submit via flash endpoint. Returns (video_bytes, data)."""
    import time

    t_req = time.time()
    n_files = (
        len(req.ref_images)
        + len(req.ref_videos)
        + len(req.ref_video_audios)
        + len(req.ref_audios)
    )
    print(f"[REQ] prompt={req.prompt[:40]}  seed={req.seed}  files={n_files}", flush=True)
    payload = build_payload(req)

    print(f"[GEN] starting ComfyUI job prompt={req.prompt[:40]}", flush=True)
    t_gen = time.time()
    job = run_comfy_endpoint(endpoint, payload)
    print(f"[GEN] ComfyUI job done in {time.time() - t_gen:.1f}s", flush=True)

    if getattr(job, "error", None):
        raise RuntimeError(f"job failed: {job.error}")

    output = getattr(job, "output", None) or job
    video_bytes, data = parse_output(output)

    print(f"[OK] submit/fetch in {time.time() - t_req:.1f}s", flush=True)
    return video_bytes, data

def do_inference(backend, storage: Storage, req: ValidatedRef2VAComfyInput) -> MiniMaxH3Ref2VAComfyOutput:
    """Beam (base_url str) and flash (endpoint) paths converge here. Testable via DI."""
    if storage is None:
        raise ValueError("storage is required")

    if isinstance(backend, str):
        video_bytes, data = _run_beam(backend, req)
    else:
        video_bytes, data = _run_flash(backend, req)

    result = upload_result(storage, video_bytes, data)
    print(f"[R2] uploaded key={result.artifact.presigned_url[:60]}", flush=True)
    return result
