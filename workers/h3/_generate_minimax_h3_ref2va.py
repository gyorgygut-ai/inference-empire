"""Shared business logic for minimax-h3-ref2va. No platform imports."""
from __future__ import annotations

import os
import time
import uuid
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from workers.services.storage.storage import Storage

MODEL_ID = "DiffSynth-Studio/MiniMax-H3-NF4"
REF2VA_WEIGHTS = "minimax-h3-ref2va-nf4.safetensors"
TEXT_ENCODER = "minimax-h3-text-encoder-nf4.safetensors"
VIDEO_VAE = "video_vae_nf4.safetensors"
AUDIO_VAE = "audio_vae_nf4.safetensors"
PROCESSOR_REPO = "MiniMaxAI/MiniMax-H3"
PROCESSOR_PATTERN = "Ref2VA/processor/"
FPS = 24

_MAX_REF_IMAGES = 9
_MAX_REF_VIDEOS = 3
_MAX_REF_AUDIOS = 3
_MAX_TOTAL_FILES = 12


class MiniMaxH3Ref2VAInput(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3Ref2VAInput")
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
    width: int = Field(default=1344)
    height: int = Field(default=768)
    length: int = Field(default=124)
    steps: int = Field(default=50)
    seed: Optional[int] = Field(default=None)


class ValidatedRef2VAInput(MiniMaxH3Ref2VAInput):
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


class MiniMaxH3Ref2VAOutput(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3Ref2VAOutput")
    artifact: Artifact


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
        kwargs = {"resample": True, "resample_rate": sample_rate}
        if duration is not None:
            kwargs["duration"] = duration
        waveform, out_rate = _read_audio(fh.name, **kwargs)
    return waveform, out_rate


def build_references(req: ValidatedRef2VAInput, pipe) -> list[dict]:
    references = []
    for i in range(len(req.ref_images)):
        references.append({"type": "image", "image": read_image(req.ref_images[i])})
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
    """Production path: always boots the real model."""
    import torch
    import torch.distributed as dist

    try:
        dist.is_available = lambda: False
    except Exception:
        pass

    from diffsynth.pipelines.minimax_h3_audio_video import (
        MiniMaxH3Pipeline,
        ModelConfig,
    )
    from diffsynth.utils.data.audio_video import write_video_audio

    vram_config = {
        "offload_dtype": "disk",
        "offload_device": "disk",
        "onload_dtype": torch.bfloat16,
        "onload_device": "cpu",
        "preparing_dtype": torch.bfloat16,
        "preparing_device": "cuda",
        "computation_dtype": torch.bfloat16,
        "computation_device": "cuda",
    }

    print(f"[INIT] loading model {MODEL_ID}", flush=True)
    t0 = time.time()
    pipe = MiniMaxH3Pipeline.from_pretrained(
        torch_dtype=torch.bfloat16,
        device="cuda",
        model_configs=[
            ModelConfig(model_id=MODEL_ID, origin_file_pattern=REF2VA_WEIGHTS, **vram_config),
            ModelConfig(model_id=MODEL_ID, origin_file_pattern=TEXT_ENCODER, **vram_config),
            ModelConfig(model_id=MODEL_ID, origin_file_pattern=VIDEO_VAE, **vram_config),
            ModelConfig(model_id=MODEL_ID, origin_file_pattern=AUDIO_VAE, **vram_config),
        ],
        processor_config=ModelConfig(
            model_id=PROCESSOR_REPO,
            origin_file_pattern=PROCESSOR_PATTERN,
        ),
        vram_limit=torch.cuda.mem_get_info("cuda")[1] / (1024**3) - vram_reserve_gb,
    )
    print(f"[INIT] model loaded in {time.time() - t0:.1f}s", flush=True)
    return pipe, write_video_audio


def load_pipeline_as_needed(pipe=None, write_video_audio=None, vram_reserve_gb: float = 5.0):
    """DI entry: injected fakes pass through, else real load."""
    if pipe is not None:
        if write_video_audio is None:
            from diffsynth.utils.data.audio_video import write_video_audio
        return pipe, write_video_audio
    return load_pipeline(vram_reserve_gb=vram_reserve_gb)


def run_generate(
    pipe,
    write_video_audio,
    storage: Storage,
    req: ValidatedRef2VAInput,
) -> MiniMaxH3Ref2VAOutput:
    """Takes validated Input, returns Output. Testable via DI."""
    import io

    if storage is None:
        raise ValueError("storage is required")

    t_req = time.time()
    total = len(req.ref_images) + len(req.ref_videos) + len(req.ref_video_audios) + len(req.ref_audios)
    print(f"[REQ] prompt={req.prompt[:40]}  seed={req.seed}  files={total}", flush=True)

    references = build_references(req, pipe)

    pipe_kwargs = {
        "prompt": req.prompt,
        "height": req.height,
        "width": req.width,
        "num_frames": req.length,
        "num_inference_steps": req.steps,
    }
    if references:
        pipe_kwargs["references"] = references
    if req.seed is not None:
        pipe_kwargs["seed"] = req.seed

    print(f"[GEN] starting inference prompt={req.prompt[:40]}", flush=True)
    t_gen = time.time()
    video, audio = pipe(**pipe_kwargs)
    print(
        f"[GEN] inference done in {time.time() - t_gen:.1f}s  "
        f"shape={video.shape[2]}x{video.shape[3]}  frames={video.shape[1]}",
        flush=True,
    )

    output_path = f"/tmp/minimax_h3_ref2va_{uuid.uuid4()}.mp4"
    try:
        write_video_audio(
            video=video,
            audio=audio,
            output_path=output_path,
            fps=FPS,
            audio_sample_rate=pipe.audio_vae.sample_rate,
        )
        with io.open(output_path, "rb") as fh:
            video_bytes = fh.read()
    finally:
        if os.path.exists(output_path):
            os.remove(output_path)

    key = f"minimax_ref2va_{uuid.uuid4()}.mp4"
    storage.put(key, video_bytes)
    presigned_url = storage.presigned_url(key)
    print(f"[R2] uploaded key={key} url={presigned_url[:60]}", flush=True)

    print(f"[OK] completed in {time.time() - t_req:.1f}s", flush=True)
    return MiniMaxH3Ref2VAOutput(artifact=Artifact(presigned_url=presigned_url))
