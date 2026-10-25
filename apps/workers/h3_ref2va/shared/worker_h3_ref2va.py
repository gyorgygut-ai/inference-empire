"""Shared business logic for minimax-h3-turbo-ref2va. No platform imports."""
from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from packages.media.validation import validate_image_b64, validate_media_b64

if TYPE_CHECKING:

    from packages.artifacts.artifacts import Artifacts

DIFFUSION_REPO = "Comfy-Org/MiniMax-H3"
DIFFUSION_WEIGHTS = "diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors"
TEXT_ENCODER_REPO = "Comfy-Org/MiniMax-H3"
TEXT_ENCODER = "text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors"
VAE_REPO = "MiniMax/MiniMax-H3"
VIDEO_VAE = "Ref2VA/video_vae/source/model.safetensors"
AUDIO_VAE = "Ref2VA/audio_vae/model.safetensors"
PROCESSOR_REPO = "MiniMax/MiniMax-H3"
PROCESSOR_PATTERN = "Ref2VA/processor/"
LORA_REPO = "lightx2v/Minimax-h3-Turbo"
LORA_WEIGHTS = "minimax_h3_ref2v_turbo_4step_v0.1_bf16.safetensors"
# Turbo LoRA fixes inference to 4 steps; shifts match v0.1 training (video 12 / audio 3).
STEPS = 4
FLOW_SHIFT = 12.0
AUDIO_FLOW_SHIFT = 3.0
FPS = 24

IMAGE_PIP_DEPS: list[str] = [
    "torch==2.9.1",
    "torchcodec==0.9.0",
    "diffsynth[audio]==2.1.6",
    "comfy-kitchen==0.2.33",
    "diffusers==0.40.0",
    "transformers==5.16.1",
    "accelerate==1.14.0",
    "bitsandbytes==0.50.2",
    "pillow==12.3.0",
    "imageio==2.37.2",
    "imageio-ffmpeg==0.6.0",
    "torchaudio==2.9.1",
    "boto3==1.43.83",
    "fastapi==0.141.1",
    "hf_transfer==0.1.9",
]

_MAX_REF_IMAGES = 9
_MAX_REF_VIDEOS = 3
_MAX_REF_AUDIOS = 3
_MAX_TOTAL_FILES = 12

class MiniMaxH3TurboRef2vaInput(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3TurboRef2vaInput")
    prompt: str = Field(
        description="Prompt describing the target shot; reference inputs by tag in connection order, e.g. <Picture 1>, <Video 1>, <Audio 1>."
    )
    ref_images: list[str] = Field(
        default=[],
        description="Up to 9 reference images as base64 data URLs (identity, style, pose).",
    )
    ref_videos: list[str] = Field(
        default=[],
        description="Up to 3 reference video clips as base64 data URLs (motion, camera, editing).",
    )
    ref_video_audios: list[str] = Field(
        default=[],
        description="Audio track paired with each reference video (index-aligned with ref_videos).",
    )
    ref_audios: list[str] = Field(
        default=[],
        description="Up to 3 standalone reference audio clips (e.g. voice).",
    )
    width: int = Field(default=960)
    height: int = Field(default=544)
    length: int = Field(default=124)
    seed: int | None = Field(default=None)

    @field_validator("ref_images")
    @classmethod
    def _check_ref_images(cls, v: list[str], info: ValidationInfo) -> list[str]:
        return [validate_image_b64(item, f"{info.field_name}[{i}]") for i, item in enumerate(v)]

    @field_validator("ref_videos", "ref_video_audios", "ref_audios")
    @classmethod
    def _check_ref_media(cls, v: list[str], info: ValidationInfo) -> list[str]:
        return [validate_media_b64(item, f"{info.field_name}[{i}]") for i, item in enumerate(v)]

class ValidatedRef2VAInput(MiniMaxH3TurboRef2vaInput):
    @field_validator("ref_images")
    @classmethod
    def _check_ref_images(cls, v: list[str], info: ValidationInfo) -> list[str]:
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
            raise ValueError(
                f"too many reference audio clips: {len(v)} (max {_MAX_REF_AUDIOS})"
            )
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
            raise ValueError(
                f"too many reference files in total: {total} (max {_MAX_TOTAL_FILES})"
            )
        return v

    @field_validator("ref_audios")
    @classmethod
    def _check_audio_not_alone(cls, v: list[str], info) -> list[str]:
        if v:
            has_visual = bool(info.data.get("ref_images")) or bool(
                info.data.get("ref_videos")
            )
            if not has_visual:
                raise ValueError(
                    "reference audio requires at least one reference image or video "
                    "(audio-only input is not supported)"
                )
        return v

class Artifact(BaseModel):
    model_config = ConfigDict(title="Artifact")
    presigned_url: str

class MiniMaxH3TurboRef2vaOutput(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3TurboRef2vaOutput")
    artifact: Artifact

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

def apply_torch_shims() -> None:
    import torch.distributed as dist

    try:
        def _dist_unavailable() -> bool:
            return False

        dist.is_available = _dist_unavailable  # ty: ignore[invalid-assignment]
    except Exception:
        pass

    import torch

    _orig_load_library = torch.ops.load_library

    def _patched_load_library(path: str) -> None:
        try:
            _orig_load_library(path)
        except OSError as e:
            raise RuntimeError(f"torch native library failed to load: {path}: {e}") from e

    torch.ops.load_library = _patched_load_library  # ty: ignore[invalid-assignment]

def read_image(base64_str: str):
    import base64
    import io

    from PIL import Image

    return Image.open(io.BytesIO(base64.b64decode(base64_str))).convert("RGB")

def read_video(base64_str: str, height: int, width: int, length: int, sample_rate: int) -> list:
    import base64
    import tempfile

    from diffsynth.utils.data.minimax_h3 import MiniMaxH3ReferenceLoader

    loader = MiniMaxH3ReferenceLoader(
        height=height,
        width=width,
        num_frames=length,
        frame_rate=FPS,
        audio_sample_rate=sample_rate,
    )
    with tempfile.NamedTemporaryFile(suffix=".mp4") as fh:
        fh.write(base64.b64decode(base64_str))
        fh.flush()
        frames = loader.load_video(fh.name)
    return frames

def read_audio(base64_str: str, sample_rate: int, duration: float | None = None) -> tuple:
    import base64
    import tempfile

    from diffsynth.utils.data.audio import read_audio as _read_audio

    with tempfile.NamedTemporaryFile(suffix=".mp3") as fh:
        fh.write(base64.b64decode(base64_str))
        fh.flush()
        kwargs: dict[str, Any] = {"resample": True, "resample_rate": sample_rate}
        if duration is not None:
            kwargs["duration"] = duration
        waveform, out_rate = _read_audio(fh.name, **kwargs)
    return waveform, out_rate

def build_references(req, pipe) -> list[dict]:
    references = []
    references = [{"type": "image", "image": read_image(img)} for img in req.ref_images]
    for i in range(len(req.ref_videos)):
        frames = read_video(
            req.ref_videos[i], req.height, req.width, req.length, pipe.audio_vae.sample_rate
        )
        if i < len(req.ref_video_audios):
            waveform, sample_rate = read_audio(
                req.ref_video_audios[i], pipe.audio_vae.sample_rate, duration=len(frames) / FPS
            )
            references.append(
                {
                    "type": "video_audio",
                    "video": frames,
                    "audio": waveform,
                    "sample_rate": sample_rate,
                }
            )
        else:
            references.append({"type": "video", "video": frames})
    for i in range(len(req.ref_audios)):
        waveform, sample_rate = read_audio(req.ref_audios[i], pipe.audio_vae.sample_rate)
        references.append(
            {"type": "audio", "audio": waveform, "sample_rate": sample_rate}
        )
    return references

def load_pipeline(vram_reserve_gb: float = 5.0):
    import torch
    import torch.distributed as dist

    try:
        def _dist_unavailable() -> bool:
            return False

        dist.is_available = _dist_unavailable  # ty: ignore[invalid-assignment]
    except Exception:
        pass

    from diffsynth.pipelines.minimax_h3_audio_video import (
        MiniMaxH3Pipeline,
        ModelConfig,
    )
    from diffsynth.utils.data.audio_video import write_video_audio

    vram_config: dict[str, Any] = {
        "offload_dtype": "disk",
        "offload_device": "disk",
        "onload_dtype": torch.bfloat16,
        "onload_device": "cpu",
        "preparing_dtype": torch.bfloat16,
        "preparing_device": "cuda",
        "computation_dtype": torch.bfloat16,
        "computation_device": "cuda",
    }

    print(f"[INIT] loading model {DIFFUSION_REPO} + turbo lora", flush=True)
    t0 = time.time()
    pipe = MiniMaxH3Pipeline.from_pretrained(
        torch_dtype=torch.bfloat16,
        device="cuda",
        model_configs=[
            ModelConfig(model_id=DIFFUSION_REPO, origin_file_pattern=DIFFUSION_WEIGHTS, **vram_config),
            ModelConfig(model_id=TEXT_ENCODER_REPO, origin_file_pattern=TEXT_ENCODER, **vram_config),
            ModelConfig(model_id=VAE_REPO, origin_file_pattern=VIDEO_VAE, **vram_config),
            ModelConfig(model_id=VAE_REPO, origin_file_pattern=AUDIO_VAE, **vram_config),
        ],
        processor_config=ModelConfig(
            model_id=PROCESSOR_REPO,
            origin_file_pattern=PROCESSOR_PATTERN,
        ),
        vram_limit=torch.cuda.mem_get_info("cuda")[1] / (1024**3) - vram_reserve_gb,
    )
    pipe.load_lora(pipe.dit, ModelConfig(model_id=LORA_REPO, origin_file_pattern=LORA_WEIGHTS))
    print(f"[INIT] model loaded in {time.time() - t0:.1f}s", flush=True)
    return pipe, write_video_audio

def do_inference(
    pipe,
    write_video_audio,
    storage: Artifacts,
    req,
) -> MiniMaxH3TurboRef2vaOutput:
    t_req = time.time()
    total = len(req.ref_images) + len(req.ref_videos) + len(req.ref_video_audios) + len(req.ref_audios)
    print(f"[REQ] prompt={req.prompt[:40]}  seed={req.seed}  files={total}", flush=True)

    references = build_references(req, pipe)

    pipe_kwargs = {
        "prompt": req.prompt,
        "height": req.height,
        "width": req.width,
        "num_frames": req.length,
        "num_inference_steps": STEPS,
        "flow_shift": FLOW_SHIFT,
        "audio_flow_shift": AUDIO_FLOW_SHIFT,
    }
    if references:
        pipe_kwargs["references"] = references
    if req.seed is not None:
        pipe_kwargs["seed"] = req.seed

    print(f"[GEN] starting turbo inference prompt={req.prompt[:40]}", flush=True)
    t_gen = time.time()
    video, audio = pipe(**pipe_kwargs)
    if isinstance(video, list):
        _size = video[0].size if video and hasattr(video[0], "size") else "?"
        _info = f"frames={len(video)} size={_size}"
    else:
        _info = f"shape={video.shape[2]}x{video.shape[3]}  frames={video.shape[1]}"
    print(
        f"[GEN] inference done in {time.time() - t_gen:.1f}s  {_info}",
        flush=True,
    )

    output_path = f"/tmp/minimax_h3_turbo_ref2va_{uuid.uuid4()}.mp4"
    try:
        write_video_audio(
            video=video,
            audio=audio,
            output_path=output_path,
            fps=FPS,
            audio_sample_rate=pipe.audio_vae.sample_rate,
        )
        with open(output_path, "rb") as fh:
            video_bytes = fh.read()
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)

    key = f"minimax_turbo_ref2va_{uuid.uuid4()}.mp4"
    storage.put(key, video_bytes)
    presigned_url = storage.presigned_url(key)
    print(f"[R2] uploaded key={key} url={presigned_url[:60]}", flush=True)

    print(f"[OK] completed in {time.time() - t_req:.1f}s", flush=True)
    return MiniMaxH3TurboRef2vaOutput(artifact=Artifact(presigned_url=presigned_url))

def pipe_factory():
    return load_pipeline()[0]

def load_dependencies(_cache_dir=None):
    from packages.artifacts.r2_artifacts import R2Artifacts

    storage = R2Artifacts()
    return storage, pipe_factory(), _WriteVideoAudioService()


class _WriteVideoAudioService:
    def __call__(self, video, audio, output_path, fps, audio_sample_rate):
        from diffsynth.utils.data.audio_video import write_video_audio as diffsynth_write

        return diffsynth_write(
            video=video,
            audio=audio,
            output_path=output_path,
            fps=fps,
            audio_sample_rate=audio_sample_rate,
        )
