import base64
import io
import os
import time
import uuid
from typing import Literal, Optional

import boto3
from PIL import Image as PILImage

from beam import Image, QueueDepthAutoscaler, Volume, task_queue
from pydantic import BaseModel, ConfigDict, Field


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


def load_pipeline():
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

    return pipe, write_video_audio


def _decode_image(base64_str: str):
    import base64
    import io
    from PIL import Image

    return Image.open(io.BytesIO(base64.b64decode(base64_str))).convert("RGB")


@task_queue(
    name="minimax-h3-fl2va-worker",
    cpu=1,
    memory="32Gi",
    gpu="RTX4090",
    image=image,
    on_start=load_pipeline,
    volumes=[Volume(name="hf-cache", mount_path=CACHE_PATH)],
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=1800,
    checkpoint_enabled=True,
    timeout=3600,
    secrets=["HF_TOKEN", "R2_ACCESS_KEY", "R2_SECRET_KEY"],
    env={
        "R2_BUCKET": "generated-media",
        "R2_ENDPOINT": "https://29b2f092b2dbc0b63f48f491ddc177ee.r2.cloudflarestorage.com",
    },
)
def generate(context, prompt: str, width: int = 1344, height: int = 768,
             length: int = 124, steps: int = 50, seed: int | None = None,
             first_frame: str | None = None, last_frame: str | None = None) -> dict:
    t_req = time.time()
    print(f"[REQ] prompt={prompt[:40]}  seed={seed}", flush=True)
    try:
        pipe, write_video_audio = context.on_start_value

        pipe_kwargs = {
            "prompt": prompt,
            "height": height,
            "width": width,
            "num_frames": length,
            "num_inference_steps": steps,
        }
        if seed is not None:
            pipe_kwargs["seed"] = seed

        keyframes = []
        keyframe_indices = []
        if first_frame:
            keyframes.append(_decode_image(first_frame))
            keyframe_indices.append(0)
        if last_frame:
            keyframes.append(_decode_image(last_frame))
            keyframe_indices.append(-1)
        if keyframes:
            pipe_kwargs["keyframes"] = keyframes
            pipe_kwargs["keyframe_indices"] = keyframe_indices

        video, audio = pipe(**pipe_kwargs)

        output_path = f"/tmp/minimax_h3_fl2va_{uuid.uuid4()}.mp4"
        write_video_audio(
            video=video,
            audio=audio,
            output_path=output_path,
            fps=24,
            audio_sample_rate=pipe.audio_vae.sample_rate,
        )

        with open(output_path, "rb") as fh:
            video_bytes = fh.read()

        bucket = os.environ.get("R2_BUCKET", "generated-media")
        endpoint = os.environ["R2_ENDPOINT"]
        access_key = os.environ["R2_ACCESS_KEY"]
        secret_key = os.environ["R2_SECRET_KEY"]
        key = f"minimax_fl2va_{uuid.uuid4()}.mp4"
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        s3.put_object(Bucket=bucket, Key=key, Body=video_bytes, ContentType="video/mp4")
        presigned_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=3600,
        )

        os.remove(output_path)

        return {"artifact": {"presigned_url": presigned_url}}
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise
