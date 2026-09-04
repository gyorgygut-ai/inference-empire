import base64
import io
import os
import time
import uuid
from typing import Literal, Optional

import boto3
from PIL import Image as PILImage
from pydantic import field_validator

from beam import Image, QueueDepthAutoscaler, Volume, task_queue
from pydantic import BaseModel, ConfigDict, Field

START_TIME = time.time()


CACHE_PATH = "./hf-cache"

image = (
    Image(python_version="python3.11")
    .add_python_packages([
        "torch==2.9.1",
        "torchcodec==0.9.0",
        "diffsynth[audio]",
        "transformers>=4.57,<5",
        "bitsandbytes",
        "pillow",
        "imageio[ffmpeg]",
        "torchaudio",
        "boto3",
    ])
    .with_envs({
        "HF_HOME": CACHE_PATH,
        "DIFFSYNTH_DOWNLOAD_SOURCE": "huggingface",
        "DIFFSYNTH_MODEL_BASE_PATH": f"{CACHE_PATH}/diffsynth",
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
    })
)


_MAX_REF_IMAGES = 9
_MAX_REF_VIDEOS = 3
_MAX_REF_AUDIOS = 3
_MAX_TOTAL_FILES = 12


class MiniMaxH3Ref2VAInput(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3Ref2VAInput")
    prompt: str = Field(
        description="Prompt describing the target shot; reference inputs by tag in connection order, e.g. <Picture 1>, <Video 1>, <Audio 1>."
    )
    ref_images: list[str] = Field(default=[], max_length=9, description="Up to 9 reference images as base64 data URLs (identity, style, pose).")
    ref_videos: list[str] = Field(default=[], max_length=3, description="Up to 3 reference video clips as base64 data URLs (motion, camera, editing).")
    ref_video_audios: list[str] = Field(default=[], max_length=3, description="Audio track paired with each reference video (index-aligned with ref_videos).")
    ref_audios: list[str] = Field(default=[], max_length=3, description="Up to 3 standalone reference audio clips (e.g. voice).")
    width: int = Field(default=1344)
    height: int = Field(default=768)
    length: int = Field(default=124)
    steps: int = Field(default=50)
    seed: Optional[int] = Field(default=None)


def _check_ref_images(cls, v: list[str]) -> list[str]:
    if len(v) > _MAX_REF_IMAGES:
        raise ValueError(f"too many reference images: {len(v)} (max {_MAX_REF_IMAGES})")
    return v


def _check_ref_videos(cls, v: list[str]) -> list[str]:
    if len(v) > _MAX_REF_VIDEOS:
        raise ValueError(f"too many reference videos: {len(v)} (max {_MAX_REF_VIDEOS})")
    return v


def _check_ref_video_audios(cls, v: list[str]) -> list[str]:
    if len(v) > _MAX_REF_VIDEOS:
        raise ValueError(f"too many reference video audio tracks: {len(v)} (max {_MAX_REF_VIDEOS})")
    return v


def _check_ref_audios(cls, v: list[str]) -> list[str]:
    if len(v) > _MAX_REF_AUDIOS:
        raise ValueError(f"too many reference audio clips: {len(v)} (max {_MAX_REF_AUDIOS})")
    return v


def _check_total_files(cls, v: list[str], info) -> list[str]:
    ref_images = info.data.get("ref_images") or []
    ref_videos = info.data.get("ref_videos") or []
    ref_video_audios = info.data.get("ref_video_audios") or []
    ref_audios = info.data.get("ref_audios") or []
    total = (
        len(v)
        + len(ref_images)
        + len(ref_videos)
        + len(ref_video_audios)
        + len(ref_audios)
    )
    if total > _MAX_TOTAL_FILES:
        raise ValueError(f"too many reference files in total: {total} (max {_MAX_TOTAL_FILES})")
    return v


def _check_audio_not_alone(cls, v: list[str], info) -> list[str]:
    if v:
        has_visual = bool(info.data.get("ref_images")) or bool(info.data.get("ref_videos"))
        if not has_visual:
            raise ValueError("reference audio requires at least one reference image or video (audio-only input is not supported)")
    return v


def _check_video_audio_pairs(cls, v: list[str], info) -> list[str]:
    ref_videos = info.data.get("ref_videos") or []
    if len(v) > len(ref_videos):
        raise ValueError(
            f"{len(v)} reference video audio tracks for {len(ref_videos)} reference videos "
            "(ref_video_audios is index-aligned with ref_videos)"
        )
    return v


def _read_image(base64_str: str):
    import base64
    import io
    from PIL import Image

    return Image.open(io.BytesIO(base64.b64decode(base64_str))).convert("RGB")


def _read_video(base64_str: str, height: int, width: int, length: int, sample_rate: int):
    import base64
    import tempfile

    from diffsynth.utils.data.minimax_h3 import MiniMaxH3ReferenceLoader

    loader = MiniMaxH3ReferenceLoader(
        height=height,
        width=width,
        num_frames=length,
        frame_rate=24,
        audio_sample_rate=sample_rate,
    )
    with tempfile.NamedTemporaryFile(suffix=".mp4") as fh:
        fh.write(base64.b64decode(base64_str))
        fh.flush()
        frames = loader.load_video(fh.name)
    return frames


def _read_audio(base64_str: str, sample_rate: int, duration: float | None = None):
    import base64
    import tempfile

    from diffsynth.utils.data.audio import read_audio

    with tempfile.NamedTemporaryFile(suffix=".mp3") as fh:
        fh.write(base64.b64decode(base64_str))
        fh.flush()
        read_kwargs = {"resample": True, "resample_rate": sample_rate}
        if duration is not None:
            read_kwargs["duration"] = duration
        waveform, sample_rate = read_audio(fh.name, **read_kwargs)
    return waveform, sample_rate


def _build_references(req, pipe) -> list[dict]:
    references = []
    for i in range(len(req.ref_images)):
        references.append({"type": "image", "image": _read_image(req.ref_images[i])})
    for i in range(len(req.ref_videos)):
        frames = _read_video(req.ref_videos[i], req.height, req.width, req.length, pipe.audio_vae.sample_rate)
        if i < len(req.ref_video_audios):
            waveform, sample_rate = _read_audio(
                req.ref_video_audios[i], pipe.audio_vae.sample_rate, duration=len(frames) / 24
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
        waveform, sample_rate = _read_audio(req.ref_audios[i], pipe.audio_vae.sample_rate)
        references.append(
            {"type": "audio", "audio": waveform, "sample_rate": sample_rate}
        )
    return references


def load_pipeline():
    t0 = time.time()
    print("[INIT] loading model DiffSynth-Studio/MiniMax-H3-NF4", flush=True)
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

    pipe = MiniMaxH3Pipeline.from_pretrained(
        torch_dtype=torch.bfloat16,
        device="cuda",
        model_configs=[
            ModelConfig(
                model_id="DiffSynth-Studio/MiniMax-H3-NF4",
                origin_file_pattern="minimax-h3-ref2va-nf4.safetensors",
                **vram_config,
            ),
            ModelConfig(
                model_id="DiffSynth-Studio/MiniMax-H3-NF4",
                origin_file_pattern="minimax-h3-text-encoder-nf4.safetensors",
                **vram_config,
            ),
            ModelConfig(
                model_id="DiffSynth-Studio/MiniMax-H3-NF4",
                origin_file_pattern="video_vae_nf4.safetensors",
                **vram_config,
            ),
            ModelConfig(
                model_id="DiffSynth-Studio/MiniMax-H3-NF4",
                origin_file_pattern="audio_vae_nf4.safetensors",
                **vram_config,
            ),
        ],
        processor_config=ModelConfig(
            model_id="MiniMaxAI/MiniMax-H3",
            origin_file_pattern="Ref2VA/processor/",
        ),
        vram_limit=torch.cuda.mem_get_info("cuda")[1] / (1024 ** 3) - 5,
    )
    print(f"[INIT] model loaded in {time.time() - t0:.1f}s", flush=True)

    return pipe, write_video_audio


@task_queue(
    name="minimax-h3-ref2va-worker",
    cpu=1,
    memory="32Gi",
    gpu="RTX4090",
    image=image,
    on_start=load_pipeline,
    volumes=[Volume(name="hf-cache", mount_path=CACHE_PATH)],
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=1800,
    timeout=3600,
    secrets=["HF_TOKEN", "R2_ACCESS_KEY", "R2_SECRET_KEY"],
    env={
        "R2_BUCKET": "generated-media",
        "R2_ENDPOINT": "https://29b2f092b2dbc0b63f48f491ddc177ee.r2.cloudflarestorage.com",
    },
)
def generate(context, prompt: str,
             ref_images: list[str] = [],
             ref_videos: list[str] = [],
             ref_video_audios: list[str] = [],
             ref_audios: list[str] = [],
             width: int = 1344, height: int = 768,
             length: int = 124, steps: int = 50, seed: int | None = None,
             storage=None) -> dict:
    t_req = time.time()
    total_files = len(ref_images) + len(ref_videos) + len(ref_video_audios) + len(ref_audios)
    print(f"[REQ] prompt={prompt[:40]}  seed={seed}  files={total_files}", flush=True)
    try:
        pipe, write_video_audio = context.on_start_value
        if storage is None:
            from services.real_r2 import RealR2Storage
            storage = RealR2Storage()

        class ValidatedInput(MiniMaxH3Ref2VAInput):
            @field_validator("ref_images")
            @classmethod
            def _check_ref_images(cls, v: list[str]) -> list[str]:
                return _check_ref_images(cls, v)

            @field_validator("ref_videos")
            @classmethod
            def _check_ref_videos(cls, v: list[str]) -> list[str]:
                return _check_ref_videos(cls, v)

            @field_validator("ref_video_audios")
            @classmethod
            def _check_ref_video_audios(cls, v: list[str]) -> list[str]:
                return _check_ref_video_audios(cls, v)

            @field_validator("ref_audios")
            @classmethod
            def _check_ref_audios(cls, v: list[str]) -> list[str]:
                return _check_ref_audios(cls, v)

            @field_validator("ref_video_audios")
            @classmethod
            def _check_video_audio_pairs(cls, v: list[str], info) -> list[str]:
                return _check_video_audio_pairs(cls, v, info)

            @field_validator("ref_audios")
            @classmethod
            def _check_audio_not_alone(cls, v: list[str], info) -> list[str]:
                return _check_audio_not_alone(cls, v, info)

            @field_validator("ref_images", "ref_videos", "ref_video_audios", "ref_audios")
            @classmethod
            def _check_total_files(cls, v: list[str], info) -> list[str]:
                return _check_total_files(cls, v, info)

            Input = ValidatedInput

        req = ValidatedInput(
            prompt=prompt,
            ref_images=ref_images,
            ref_videos=ref_videos,
            ref_video_audios=ref_video_audios,
            ref_audios=ref_audios,
            width=width,
            height=height,
            length=length,
            steps=steps,
            seed=seed,
        )

        references = _build_references(req, pipe)

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

        print(f"[GEN] inference done in {time.time() - t_gen:.1f}s  shape={video.shape[2]}x{video.shape[3]}  frames={video.shape[1]}", flush=True)

        output_path = f"/tmp/minimax_h3_ref2va_{uuid.uuid4()}.mp4"
        write_video_audio(
            video=video,
            audio=audio,
            output_path=output_path,
            fps=24,
            audio_sample_rate=pipe.audio_vae.sample_rate,
        )

        with open(output_path, "rb") as fh:
            video_bytes = fh.read()

        key = f"minimax_ref2va_{uuid.uuid4()}.mp4"
        storage.put(key, video_bytes)
        presigned_url = storage.presigned_url(key)
        print(f"[R2] uploaded key={key} url={presigned_url[:60]}", flush=True)

        os.remove(output_path)

        print(f"[OK] completed in {time.time() - START_TIME:.1f}s", flush=True)

        return {"artifact": {"presigned_url": presigned_url}}
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise
