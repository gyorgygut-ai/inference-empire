import base64
import io
import os
import time
import uuid
from typing import Literal, Optional

import modal
from pydantic import BaseModel, ConfigDict, Field

app = modal.App("minimax-h3-fl2va-worker")

r2_secret = modal.Secret.from_name(
    "r2-creds", required_keys=["R2_BUCKET", "R2_ENDPOINT", "R2_ACCESS_KEY", "R2_SECRET_KEY"]
)


class MiniMaxH3Fl2VAInput(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3Fl2VAInput")
    prompt: str
    width: int = Field(default=1344)
    height: int = Field(default=768)
    length: int = Field(default=124)
    steps: int = Field(default=50)
    seed: Optional[int] = Field(default=None)
    first_frame: Optional[str] = Field(default=None)
    last_frame: Optional[str] = Field(default=None)


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
    gpu="L4",
    secrets=[r2_secret],
    timeout=900,
    memory=32768,
    scaledown_window=150,
    max_containers=1,
)
class MiniMaxH3Fl2VAWorker:
    @modal.enter()
    def load(self):
        from services.real_r2 import RealR2Storage
        self.storage = RealR2Storage()

        import torch.distributed as dist

        dist.is_available = lambda: False

        import torch
        # Modal L4 lacks libcudart.so.13 — patch load_library so torchaudio import doesn't crash
        _orig_load_library = torch.ops.load_library
        def _patched_load_library(path):
            try:
                return _orig_load_library(path)
            except OSError:
                pass
        torch.ops.load_library = _patched_load_library

        import torch
        from diffsynth.pipelines.minimax_h3_audio_video import (
            MiniMaxH3Pipeline,
            ModelConfig,
        )
        from diffsynth.utils.data.audio_video import write_video_audio

        self.torch = torch
        print('[INIT] loading model DiffSynth-Studio/MiniMax-H3-NF4', flush=True)
        t0 = time.time()
        self.write_video_audio = write_video_audio

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
                    origin_file_pattern="minimax-h3-fl2va-nf4.safetensors",
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
                origin_file_pattern="FL2VA/processor/",
            ),
            vram_limit=torch.cuda.mem_get_info("cuda")[1] / (1024**3) - 4,
        )

    def _decode_image(self, base64_str: str):
        from PIL import Image

        return Image.open(io.BytesIO(base64.b64decode(base64_str))).convert("RGB")

    @modal.method()
    def generate(
        self,
        prompt: str,
        width: int = 1344,
        height: int = 768,
        length: int = 124,
        steps: int = 50,
        seed: Optional[int] = None,
        first_frame: Optional[str] = None,
        last_frame: Optional[str] = None,
    ) -> dict:
        t_req = time.time()
        print(f"[REQ] prompt={prompt[:40]}  seed={seed}", flush=True)
        try:
            import boto3

            req = MiniMaxH3Fl2VAInput(
                prompt=prompt,
                width=width,
                height=height,
                length=length,
                steps=steps,
                seed=seed,
                first_frame=first_frame,
                last_frame=last_frame,
            )

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
                keyframes.append(self._decode_image(req.first_frame))
                keyframe_indices.append(0)
            if req.last_frame:
                keyframes.append(self._decode_image(req.last_frame))
                keyframe_indices.append(-1)
            if keyframes:
                pipe_kwargs["keyframes"] = keyframes
                pipe_kwargs["keyframe_indices"] = keyframe_indices

            video, audio = self.pipe(**pipe_kwargs)

            print(f"[GEN] inference done in {time.time() - t_req:.1f}s  shape={video.shape[2]}x{video.shape[3]}  frames={video.shape[1]}", flush=True)

            self.write_video_audio(
                video=video,
                audio=audio,
                output_path="/tmp/minimax_h3_fl2va.mp4",
                fps=24,
                audio_sample_rate=self.pipe.audio_vae.sample_rate,
            )

            with io.open("/tmp/minimax_h3_fl2va.mp4", "rb") as fh:
                video_bytes = fh.read()

            key = f"minimax_fl2va_{uuid.uuid4()}.mp4"
            self.storage.put(key, video_bytes)
            presigned_url = self.storage.presigned_url(key)
            print(f"[R2] uploaded key={key} url={presigned_url[:60]}", flush=True)

            print(f"[OK] completed in {time.time() - t_req:.1f}s", flush=True)

            return {"artifact": {"presigned_url": presigned_url}}

        except Exception as e:
            print(f"[ERR] {type(e).__name__}: {e}", flush=True)
            raise
    @modal.fastapi_endpoint(method="POST")
    def generate_web(self, item: MiniMaxH3Fl2VAInput) -> dict:
        return self.generate.local(
            prompt=item.prompt,
            width=item.width,
            height=item.height,
            length=item.length,
            steps=item.steps,
            seed=item.seed,
            first_frame=item.first_frame,
            last_frame=item.last_frame,
        )
