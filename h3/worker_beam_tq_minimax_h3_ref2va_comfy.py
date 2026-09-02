import base64
import os
import subprocess
import time
import uuid
from typing import Literal, Optional

import boto3
import requests
from pydantic import BaseModel, ConfigDict, Field, field_validator

from beam import Image, QueueDepthAutoscaler, Volume, task_queue


CACHE_PATH = "./hf-cache"

image = Image.from_registry(
    "ghcr.io/vincezh2000/minimax-h3-comfyui-serverless:cu130",
).with_envs({
    "HF_HOME": CACHE_PATH,
    "DIFFSYNTH_DOWNLOAD_SOURCE": "huggingface",
    "DIFFSYNTH_MODEL_BASE_PATH": f"{CACHE_PATH}/diffsynth",
    "HF_HUB_ENABLE_HF_TRANSFER": "1",
})


MODEL_FILES = {
    "unet_name": "minimax_h3_ref2va_pruned_int8_convrot.safetensors",
    "clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
    "vae_video_name": "minimax_h3_video_vae_fp16.safetensors",
    "vae_audio_name": "minimax_h3_audio_vae_fp32.safetensors",
}


class Input(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3Ref2VAComfyInput")
    prompt: str = Field(
        description="Prompt describing the target shot; reference inputs by tag, e.g. <Picture 1>, <Video 1>, <Audio 1>."
    )
    ref_images: list[str] = Field(default=[], max_length=9, description="Up to 9 reference images as base64 data URLs.")
    ref_videos: list[str] = Field(default=[], max_length=3, description="Up to 3 reference video clips as base64 data URLs.")
    ref_video_audios: list[str] = Field(default=[], max_length=3, description="Audio track paired with each reference video (index-aligned with ref_videos).")
    ref_audios: list[str] = Field(default=[], max_length=3, description="Up to 3 standalone reference audio clips.")
    width: int = Field(default=1344)
    height: int = Field(default=768)
    length: int = Field(default=124)
    steps: int = Field(default=20)
    seed: Optional[int] = Field(default=None)
    ref_image_size: Literal["match", "max"] = Field(default="match")
    scheduler: Literal["simple", "beta", "normal"] = Field(default="simple")


class ValidatedInput(Input):
    @field_validator("ref_images")
    @classmethod
    def _check_ref_images(cls, v: list[str]) -> list[str]:
        if len(v) > 9:
            raise ValueError(f"too many reference images: {len(v)} (max 9)")
        return v

    @field_validator("ref_videos")
    @classmethod
    def _check_ref_videos(cls, v: list[str]) -> list[str]:
        if len(v) > 3:
            raise ValueError(f"too many reference videos: {len(v)} (max 3)")
        return v

    @field_validator("ref_video_audios")
    @classmethod
    def _check_ref_video_audios(cls, v: list[str]) -> list[str]:
        if len(v) > 3:
            raise ValueError(f"too many reference video audio tracks: {len(v)} (max 3)")
        return v

    @field_validator("ref_audios")
    @classmethod
    def _check_ref_audios(cls, v: list[str]) -> list[str]:
        if len(v) > 3:
            raise ValueError(f"too many reference audio clips: {len(v)} (max 3)")
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

    @field_validator("ref_audios")
    @classmethod
    def _check_audio_not_alone(cls, v: list[str], info) -> list[str]:
        if v:
            has_visual = bool(info.data.get("ref_images")) or bool(info.data.get("ref_videos"))
            if not has_visual:
                raise ValueError("reference audio requires at least one reference image or video")
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
        if total > 12:
            raise ValueError(f"too many reference files in total: {total} (max 12)")
        return v


def _build_workflow(req) -> dict:
    workflow = {
        "unet": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": MODEL_FILES["unet_name"],
                "weight_dtype": "default",
            },
        },
        "clip": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": MODEL_FILES["clip_name"],
                "type": "minimax",
                "device": "default",
            },
        },
        "vae_video": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": MODEL_FILES["vae_video_name"]},
        },
        "vae_audio": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": MODEL_FILES["vae_audio_name"]},
        },
        "cond": {
            "class_type": "MiniMaxH3ReferenceToVideo",
            "inputs": {
                "clip": ["clip", 0],
                "vae": ["vae_video", 0],
                "audio_vae": ["vae_audio", 0],
                "prompt": req.prompt,
                "width": req.width,
                "height": req.height,
                "length": req.length,
                "ref_image_size": req.ref_image_size,
            },
        },
        "noise": {
            "class_type": "RandomNoise",
            "inputs": {"noise_seed": req.seed if req.seed is not None else 42},
        },
        "guider": {
            "class_type": "BasicGuider",
            "inputs": {
                "model": ["unet", 0],
                "conditioning": ["cond", 0],
            },
        },
        "sampler_select": {
            "class_type": "KSamplerSelect",
            "inputs": {"sampler_name": "res_multistep"},
        },
        "sigmas": {
            "class_type": "BasicScheduler",
            "inputs": {
                "model": ["unet", 0],
                "scheduler": req.scheduler,
                "steps": req.steps,
                "denoise": 1.0,
            },
        },
        "sample": {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {
                "noise": ["noise", 0],
                "guider": ["guider", 0],
                "sampler": ["sampler_select", 0],
                "sigmas": ["sigmas", 0],
                "latent_image": ["cond", 1],
            },
        },
        "decode_video": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["sample", 0],
                "vae": ["vae_video", 0],
            },
        },
        "decode_audio": {
            "class_type": "VAEDecodeAudio",
            "inputs": {
                "samples": ["sample", 0],
                "vae": ["vae_audio", 0],
            },
        },
        "video": {
            "class_type": "CreateVideo",
            "inputs": {
                "images": ["decode_video", 0],
                "fps": 24,
                "audio": ["decode_audio", 0],
            },
        },
        "save": {
            "class_type": "SaveVideo",
            "inputs": {
                "video": ["video", 0],
                "filename_prefix": "video/MiniMax_H3_Ref2VA",
                "format": "auto",
                "codec": "auto",
            },
        },
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


def _build_images(req) -> list[dict]:
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


def _start_comfy():
    proc = subprocess.Popen(
        [
            "python", "-m", "comfyui",
            "--listen", "127.0.0.1",
            "--port", "8188",
            "--disable-auto-update",
            "--dont-print-server",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(60):
        try:
            r = requests.get("http://127.0.0.1:8188/system_stats", timeout=2)
            if r.status_code == 200:
                break
        except requests.ConnectionError:
            pass
        if proc.poll() is not None:
            raise RuntimeError(f"ComfyUI server exited with code {proc.returncode}")
        time.sleep(1)
    else:
        raise RuntimeError("ComfyUI server did not become ready within 60s")
    print("[INIT] ComfyUI server ready", flush=True)

    return "http://127.0.0.1:8188"


@task_queue(
    name="minimax-h3-ref2va-comfy-worker",
    cpu=1,
    memory="32Gi",
    gpu="RTX4090",
    image=image,
    on_start=_start_comfy,
    volumes=[Volume(name="hf-cache", mount_path=CACHE_PATH)],
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=0,
    checkpoint_enabled=True,
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
             length: int = 124, steps: int = 20, seed: int | None = None,
             ref_image_size: str = "match", scheduler: str = "simple") -> dict:
    t_req = time.time()
    n_files = len(ref_images) + len(ref_videos) + len(ref_video_audios) + len(ref_audios)
    print(f"[REQ] prompt={prompt[:40]}  seed={seed}  files={n_files}", flush=True)
    comfy_base_url = context.on_start_value

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
        ref_image_size=ref_image_size,
        scheduler=scheduler,
    )

    payload = {"workflow": _build_workflow(req)}
    images = _build_images(req)
    if images:
        payload["images"] = images

    print(f"[GEN] starting ComfyUI job prompt={prompt[:40]}", flush=True)
    t_gen = time.time()
    r = requests.post(f"{comfy_base_url}/prompt", json=payload, timeout=30)
    r.raise_for_status()
    prompt_id = r.json()["prompt_id"]

    for _ in range(600):
        try:
            r = requests.get(f"{comfy_base_url}/history/{prompt_id}", timeout=10)
            history = r.json()
            if prompt_id in history:
                outputs = history[prompt_id]["outputs"]
                save_node = outputs.get("save", {})
                video_info = (save_node.get("videos") or save_node.get("gifs") or [None])[0]
                if video_info:
                    break
        except Exception:
            pass
        time.sleep(1)
    else:
        raise RuntimeError(f"ComfyUI job {prompt_id} did not complete within 600s")

    print(f"[GEN] ComfyUI job done in {time.time() - t_gen:.1f}s", flush=True)
    video_url = f"{comfy_base_url}/view?filename={video_info['filename']}&subfolder={video_info.get('subfolder', '')}&type={video_info.get('type', 'output')}"
    video_bytes = requests.get(video_url, timeout=60).content

    bucket = os.environ.get("R2_BUCKET", "generated-media")
    endpoint = os.environ["R2_ENDPOINT"]
    access_key = os.environ["R2_ACCESS_KEY"]
    secret_key = os.environ["R2_SECRET_KEY"]
    key = f"minimax_ref2va_comfy_{uuid.uuid4()}.mp4"
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
    print(f"[R2] uploaded key={key} url={presigned_url[:60]}", flush=True)

    print(f"[OK] completed in {time.time() - t_req:.1f}s", flush=True)
    return {"artifact": {"presigned_url": presigned_url}}
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise
