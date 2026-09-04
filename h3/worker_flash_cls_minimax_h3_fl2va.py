import os
import uuid

import boto3
from runpod_flash import Endpoint, GpuGroup


@Endpoint(
    name="minimax-h3-fl2va-worker",
    gpu=[GpuGroup.AMPERE_24],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env={
        "HF_HOME": "/runpod-volume/huggingface-cache",
        "DIFFSYNTH_DOWNLOAD_SOURCE": "huggingface",
        "DIFFSYNTH_MODEL_BASE_PATH": "/runpod-volume/huggingface-cache/diffsynth",
        "FLASH_TEMPLATE_SALT": "fl2va",
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
class MiniMaxH3Fl2VAWorker:
    # --- BEGIN CONTRACT: minimax_h3_fl2va (generated; run make gen-contracts) ---
    from pydantic import BaseModel

    class Input(BaseModel):
        from typing import Literal as _Literal, Optional as _Optional
        from pydantic import BaseModel as _BaseModel, ConfigDict as _ConfigDict, Field as _Field

        model_config = _ConfigDict(title='MiniMaxH3Fl2VAInput')
        prompt: str
        width: int = _Field(default=1344)
        height: int = _Field(default=768)
        length: int = _Field(default=124)
        steps: int = _Field(default=50)
        seed: _Optional[int] = _Field(default=None)
        first_frame: _Optional[str] = _Field(default=None)
        last_frame: _Optional[str] = _Field(default=None)
    # --- END CONTRACT: minimax_h3_fl2va ---




















    def __init__(self, storage=None):
        if storage:
            self.storage = storage
        else:
            from services.real_r2 import RealR2Storage
            self.storage = RealR2Storage()

        import torch.distributed as dist
        dist.is_available = lambda: False

        import torch
        from diffsynth.pipelines.minimax_h3_audio_video import (
            MiniMaxH3Pipeline,
            ModelConfig,
        )
        from diffsynth.utils.data.audio_video import write_video_audio

        self.torch = torch
        self.write_video_audio = write_video_audio

        # Values match the official DiffSynth-Studio/MiniMax-H3-NF4 README:
        # disk offload streams weights through the DiskMap so the full state
        # dict is never materialized on the GPU (the OOM cause).
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
            vram_limit=torch.cuda.mem_get_info("cuda")[1] / (1024 ** 3) - 4,
        )

    def _decode_image(self, base64_str: str):
        import base64
        import io
        from PIL import Image

        return Image.open(io.BytesIO(base64.b64decode(base64_str))).convert("RGB")

    def generate(
        self,
        prompt: str,
        width: int = 1344,
        height: int = 768,
        length: int = 124,
        steps: int = 50,
        seed: int | None = None,
        first_frame: str | None = None,
        last_frame: str | None = None,
    ) -> dict:
        import base64
        import io

        req = self.Input(
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

        return {"artifact": {"presigned_url": presigned_url}}