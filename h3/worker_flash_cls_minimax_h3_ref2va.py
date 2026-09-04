import os
import uuid

import boto3
from runpod_flash import Endpoint, GpuGroup

from pydantic import field_validator

_MAX_REF_IMAGES = 9
_MAX_REF_VIDEOS = 3
_MAX_REF_AUDIOS = 3
_MAX_TOTAL_FILES = 12


@Endpoint(
    name="minimax-h3-ref2va-worker",
    gpu=[GpuGroup.AMPERE_48],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env={
        "HF_HOME": "/runpod-volume/huggingface-cache",
        "DIFFSYNTH_DOWNLOAD_SOURCE": "huggingface",
        "DIFFSYNTH_MODEL_BASE_PATH": "/runpod-volume/huggingface-cache/diffsynth",
        "FLASH_TEMPLATE_SALT": "ref2va",
        "R2_BUCKET": os.environ.get("R2_BUCKET", "generated-media"),
        "R2_ENDPOINT": os.environ.get("R2_ENDPOINT", ""),
        "R2_ACCESS_KEY": os.environ.get("R2_ACCESS_KEY", ""),
        "R2_SECRET_KEY": os.environ.get("R2_SECRET_KEY", ""),
    },
    dependencies=[
        "torch==2.9.1",
        "torchcodec==0.9.0",
        "diffsynth[audio]",
        "transformers>=4.57,<5",
        "bitsandbytes",
        "pillow",
        "imageio[ffmpeg]",
        "torchaudio",
        "boto3",
    ],
)
class MiniMaxH3Ref2VAWorker:
    _MAX_REF_IMAGES = 9
    _MAX_REF_VIDEOS = 3
    _MAX_REF_AUDIOS = 3
    _MAX_TOTAL_FILES = 12

    # --- BEGIN CONTRACT: minimax_h3_ref2va (generated; run make gen-contracts) ---
    from pydantic import BaseModel

    class Input(BaseModel):
        from typing import Literal as _Literal, Optional as _Optional
        from pydantic import BaseModel as _BaseModel, ConfigDict as _ConfigDict, Field as _Field

        model_config = _ConfigDict(title='MiniMaxH3Ref2VAInput')
        prompt: str = _Field(description='Prompt describing the target shot; reference inputs by tag in connection order, e.g. <Picture 1>, <Video 1>, <Audio 1>.')
        ref_images: list[str] = _Field(default=[], max_length=9, description='Up to 9 reference images as base64 data URLs (identity, style, pose).')
        ref_videos: list[str] = _Field(default=[], max_length=3, description='Up to 3 reference video clips as base64 data URLs (motion, camera, editing).')
        ref_video_audios: list[str] = _Field(default=[], max_length=3, description='Audio track paired with each reference video (index-aligned with ref_videos).')
        ref_audios: list[str] = _Field(default=[], max_length=3, description='Up to 3 standalone reference audio clips (e.g. voice).')
        width: int = _Field(default=1344)
        height: int = _Field(default=768)
        length: int = _Field(default=124)
        steps: int = _Field(default=50)
        seed: _Optional[int] = _Field(default=None)

    # --- END CONTRACT: minimax_h3_ref2va ---




















    def __init__(self, storage):
        self.storage = storage

        import torch.distributed as dist
        dist.is_available = lambda: False

        import torch
        from diffsynth.pipelines.minimax_h3_audio_video import (
            MiniMaxH3Pipeline,
            ModelConfig,
        )
        from diffsynth.utils.data.audio_video import write_video_audio
        from diffsynth.utils.data.audio import read_audio

        from pydantic import field_validator

        max_images = self._MAX_REF_IMAGES
        max_videos = self._MAX_REF_VIDEOS
        max_audios = self._MAX_REF_AUDIOS
        max_total = self._MAX_TOTAL_FILES

        class ValidatedInput(self.Input):
            @field_validator("ref_images")
            @classmethod
            def _check_ref_images(cls, v: list[str]) -> list[str]:
                if len(v) > max_images:
                    raise ValueError(f"too many reference images: {len(v)} (max {max_images})")
                return v

            @field_validator("ref_videos")
            @classmethod
            def _check_ref_videos(cls, v: list[str]) -> list[str]:
                if len(v) > max_videos:
                    raise ValueError(f"too many reference videos: {len(v)} (max {max_videos})")
                return v

            @field_validator("ref_video_audios")
            @classmethod
            def _check_ref_video_audios(cls, v: list[str]) -> list[str]:
                if len(v) > max_videos:
                    raise ValueError(f"too many reference video audio tracks: {len(v)} (max {max_videos})")
                return v

            @field_validator("ref_audios")
            @classmethod
            def _check_ref_audios(cls, v: list[str]) -> list[str]:
                if len(v) > max_audios:
                    raise ValueError(f"too many reference audio clips: {len(v)} (max {max_audios})")
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
                if total > max_total:
                    raise ValueError(f"too many reference files in total: {total} (max {max_total})")
                return v

            @field_validator("ref_audios")
            @classmethod
            def _check_audio_not_alone(cls, v: list[str], info) -> list[str]:
                if v:
                    has_visual = bool(info.data.get("ref_images")) or bool(info.data.get("ref_videos"))
                    if not has_visual:
                        raise ValueError("reference audio requires at least one reference image or video (audio-only input is not supported)")
                return v

        self.Input = ValidatedInput

        self.torch = torch
        self.write_video_audio = write_video_audio
        self.read_audio = read_audio

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

        self.pipe = MiniMaxH3Pipeline.from_pretrained(
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

    def _read_image(self, base64_str: str):
        import base64
        import io
        from PIL import Image

        return Image.open(io.BytesIO(base64.b64decode(base64_str))).convert("RGB")

    def _read_video(self, base64_str: str, req) -> list:
        import base64
        import tempfile

        from diffsynth.utils.data.minimax_h3 import MiniMaxH3ReferenceLoader

        loader = MiniMaxH3ReferenceLoader(
            height=req.height,
            width=req.width,
            num_frames=req.length,
            frame_rate=24,
            audio_sample_rate=self.pipe.audio_vae.sample_rate,
        )
        with tempfile.NamedTemporaryFile(suffix=".mp4") as fh:
            fh.write(base64.b64decode(base64_str))
            fh.flush()
            frames = loader.load_video(fh.name)
        return frames

    def _read_audio(self, base64_str: str) -> tuple:
        import base64
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".mp3") as fh:
            fh.write(base64.b64decode(base64_str))
            fh.flush()
            waveform, sample_rate = self.read_audio(
                fh.name,
                resample=True,
                resample_rate=self.pipe.audio_vae.sample_rate,
            )
        return waveform, sample_rate

    def _build_references(self, req) -> list[dict]:
        references = []
        for i, _ in enumerate(req.ref_images):
            references.append({"type": "image", "image": self._read_image(req.ref_images[i])})
        for i, _ in enumerate(req.ref_videos):
            frames = self._read_video(req.ref_videos[i], req)
            if i < len(req.ref_video_audios):
                waveform, sample_rate = self._read_audio(req.ref_video_audios[i])
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
        for i, _ in enumerate(req.ref_audios):
            waveform, sample_rate = self._read_audio(req.ref_audios[i])
            references.append(
                {"type": "audio", "audio": waveform, "sample_rate": sample_rate}
            )
        return references

    def generate(
        self,
        prompt: str,
        ref_images: list[str] = [],
        ref_videos: list[str] = [],
        ref_video_audios: list[str] = [],
        ref_audios: list[str] = [],
        width: int = 1344,
        height: int = 768,
        length: int = 124,
        steps: int = 50,
        seed: int | None = None,
    ) -> dict:
        import base64
        import io

        req = self.Input(
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

        references = self._build_references(req)

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

        video, audio = self.pipe(**pipe_kwargs)

        self.write_video_audio(
            video=video,
            audio=audio,
            output_path="/tmp/minimax_h3_ref2va.mp4",
            fps=24,
            audio_sample_rate=self.pipe.audio_vae.sample_rate,
        )

        with io.open("/tmp/minimax_h3_ref2va.mp4", "rb") as fh:
            video_bytes = fh.read()

        key = f"minimax_ref2va_{uuid.uuid4()}.mp4"
        self.storage.put(key, video_bytes)
        presigned_url = self.storage.presigned_url(key)

        return {"artifact": {"presigned_url": presigned_url}}