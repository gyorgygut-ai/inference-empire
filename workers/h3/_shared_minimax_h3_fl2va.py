"""Shared business logic for minimax-h3-fl2va. No platform imports."""
from __future__ import annotations

import os
import time
import uuid
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from diffsynth.pipelines.minimax_h3_audio_video import MiniMaxH3Pipeline

    from workers.services.storage.storage import Storage

MODEL_ID = "DiffSynth-Studio/MiniMax-H3-NF4"
FL2VA_WEIGHTS = "minimax-h3-fl2va-nf4.safetensors"
TEXT_ENCODER = "minimax-h3-text-encoder-nf4.safetensors"
VIDEO_VAE = "video_vae_nf4.safetensors"
AUDIO_VAE = "audio_vae_nf4.safetensors"
PROCESSOR_REPO = "MiniMaxAI/MiniMax-H3"
PROCESSOR_PATTERN = "FL2VA/processor/"
FPS = 24


class MiniMaxH3Fl2VAInput(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3Fl2VAInput")
    prompt: str
    width: int = Field(default=1344)
    height: int = Field(default=768)
    length: int = Field(default=124)
    steps: int = Field(default=50)
    seed: int | None = Field(default=None)
    first_frame: str | None = Field(default=None)
    last_frame: str | None = Field(default=None)


class Artifact(BaseModel):
    model_config = ConfigDict(title="Artifact")
    presigned_url: str


class MiniMaxH3Fl2VAOutput(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3Fl2VAOutput")
    artifact: Artifact


def decode_image(base64_str: str):
    import base64
    import io

    from PIL import Image

    return Image.open(io.BytesIO(base64.b64decode(base64_str))).convert("RGB")


def load_pipeline(vram_reserve_gb: float = 4.0):
    """Production path: always boots the real model."""
    import torch
    import torch.distributed as dist

    try:
        dist.is_available = lambda: False
    except Exception:  # noqa: BLE001, S110
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
            ModelConfig(model_id=MODEL_ID, origin_file_pattern=FL2VA_WEIGHTS, **vram_config),
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


def load_pipeline_as_needed(pipe=None, write_video_audio=None, vram_reserve_gb: float = 4.0):
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
    req: MiniMaxH3Fl2VAInput,
) -> MiniMaxH3Fl2VAOutput:
    """Takes validated Input, returns Output. Testable via DI."""

    if storage is None:
        raise ValueError("storage is required")

    t_req = time.time()
    print(f"[REQ] prompt={req.prompt[:40]}  seed={req.seed}", flush=True)

    pipe_kwargs = {
        "prompt": req.prompt,
        "height": req.height,
        "width": req.width,
        "num_frames": req.length,
        "num_inference_steps": req.steps,
    }
    if req.seed is not None:
        pipe_kwargs["seed"] = req.seed

    keyframes = []
    keyframe_indices = []
    if req.first_frame:
        keyframes.append(decode_image(req.first_frame))
        keyframe_indices.append(0)
    if req.last_frame:
        keyframes.append(decode_image(req.last_frame))
        keyframe_indices.append(-1)
    if keyframes:
        pipe_kwargs["keyframes"] = keyframes
        pipe_kwargs["keyframe_indices"] = keyframe_indices

    print(f"[GEN] starting inference prompt={req.prompt[:40]}", flush=True)
    t_gen = time.time()
    video, audio = pipe(**pipe_kwargs)
    print(
        f"[GEN] inference done in {time.time() - t_gen:.1f}s  "
        f"shape={video.shape[2]}x{video.shape[3]}  frames={video.shape[1]}",
        flush=True,
    )

    output_path = f"/tmp/minimax_h3_fl2va_{uuid.uuid4()}.mp4"
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

    key = f"minimax_fl2va_{uuid.uuid4()}.mp4"
    storage.put(key, video_bytes)
    presigned_url = storage.presigned_url(key)
    print(f"[R2] uploaded key={key} url={presigned_url[:60]}", flush=True)

    print(f"[OK] completed in {time.time() - t_req:.1f}s", flush=True)
    return MiniMaxH3Fl2VAOutput(artifact=Artifact(presigned_url=presigned_url))


def pipe_factory() -> MiniMaxH3Pipeline:
    """Factory for the minimax-h3 pipeline."""
    return load_pipeline()[0]


def load_dependencies(cache_dir=None):
    """Load all dependencies for minimax-h3-fl2va worker."""
    from workers.services.write_video_audio.write_video_audio_real import (
        RealWriteVideoAudio,
    )

    return pipe_factory(), RealWriteVideoAudio()
