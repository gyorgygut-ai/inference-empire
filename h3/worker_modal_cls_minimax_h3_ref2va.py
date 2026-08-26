import base64
import io
import os
import uuid
from typing import Literal, Optional

import modal
from pydantic import BaseModel, ConfigDict, Field, field_validator

app = modal.App("minimax-h3-ref2va-worker")

r2_secret = modal.Secret.from_name(
    "r2-creds", required_keys=["R2_BUCKET", "R2_ENDPOINT", "R2_ACCESS_KEY", "R2_SECRET_KEY"]
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
    ref_images: list[str] = Field(
        default=[], max_length=9,
        description="Up to 9 reference images as base64 data URLs (identity, style, pose)."
    )
    ref_videos: list[str] = Field(
        default=[], max_length=3,
        description="Up to 3 reference video clips as base64 data URLs (motion, camera, editing)."
    )
    ref_video_audios: list[str] = Field(
        default=[], max_length=3,
        description="Audio track paired with each reference video (index-aligned with ref_videos)."
    )
    ref_audios: list[str] = Field(
        default=[], max_length=3,
        description="Up to 3 standalone reference audio clips (e.g. voice)."
    )
    width: int = Field(default=1344)
    height: int = Field(default=768)
    length: int = Field(default=124)
    steps: int = Field(default=50)
    seed: Optional[int] = Field(default=None)


class MiniMaxH3Ref2VAOutput(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3Ref2VAOutput")

    class Artifact(BaseModel):
        model_config = ConfigDict(title="Artifact")
        url: str
        key: str
        size: int

    artifact: Artifact


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


image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg", "libgl1", "libglib2.0-0")
    .pip_install(
        "torch==2.9.1",
        "torchcodec==0.9.0",
        "diffsynth[audio]",
        "transformers>=4.57,<5",
        "bitsandbytes",
        "pillow",
        "imageio[ffmpeg]",
        "torchaudio",
        "boto3",
        "fastapi",
        "hf_transfer",
    )
    .env(
        {
            "HF_HOME": "/root/.cache/huggingface",
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "DIFFSYNTH_DOWNLOAD_SOURCE": "huggingface",
            "DIFFSYNTH_MODEL_BASE_PATH": "/root/.cache/huggingface/diffsynth",
        }
    )
)


@app.cls(
    image=image,
    gpu="L40S",
    secrets=[r2_secret],
    timeout=900,
    memory=65536,
    scaledown_window=150,
    max_containers=1,
)
@modal.concurrent(max_inputs=4)
class MiniMaxH3Ref2VAWorker:
    @modal.enter()
    def load(self):
        import torch.distributed as dist

        dist.is_available = lambda: False

        import torch
        from diffsynth.pipelines.minimax_h3_audio_video import (
            MiniMaxH3Pipeline,
            ModelConfig,
        )
        from diffsynth.utils.data.audio_video import write_video_audio
        from diffsynth.utils.data.audio import read_audio

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
            vram_limit=torch.cuda.mem_get_info("cuda")[1] / (1024**3) - 5,
        )

    def _read_image(self, base64_str: str):
        from PIL import Image

        return Image.open(io.BytesIO(base64.b64decode(base64_str))).convert("RGB")

    def _read_video(self, base64_str: str, req) -> list:
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

    @modal.method()
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
        seed: Optional[int] = None,
    ) -> dict:
        import boto3

        req = ValidatedRef2VAInput(
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

        bucket = os.environ.get("R2_BUCKET", "generated-media")
        endpoint = os.environ.get("R2_ENDPOINT")
        access_key = os.environ.get("R2_ACCESS_KEY")
        secret_key = os.environ.get("R2_SECRET_KEY")

        key = f"minimax_ref2va_{uuid.uuid4()}.mp4"
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        s3.put_object(Bucket=bucket, Key=key, Body=video_bytes, ContentType="video/mp4")
        url = f"{endpoint.rstrip('/')}/{bucket}/{key}"

        return MiniMaxH3Ref2VAOutput(
            artifact=MiniMaxH3Ref2VAOutput.Artifact(url=url, key=key, size=len(video_bytes))
        ).model_dump()

    @modal.fastapi_endpoint(method="POST")
    def generate_web(self, item: MiniMaxH3Ref2VAInput) -> dict:
        return self.generate.local(
            prompt=item.prompt,
            ref_images=item.ref_images,
            ref_videos=item.ref_videos,
            ref_video_audios=item.ref_video_audios,
            ref_audios=item.ref_audios,
            width=item.width,
            height=item.height,
            length=item.length,
            steps=item.steps,
            seed=item.seed,
        )
