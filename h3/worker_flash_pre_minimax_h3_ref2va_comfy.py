import os
import time
import uuid

import boto3
from pydantic import field_validator

from runpod_flash import Endpoint, GpuGroup, PodTemplate


@Endpoint(
    name="minimax-h3-ref2va-comfy-worker",
    gpu=[GpuGroup.ADA_32_PRO],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    execution_timeout_ms=3600_000,
    template=PodTemplate(containerDiskInGb=150),
    env={
        "HF_HOME": "/runpod-volume/huggingface-cache",
        "R2_BUCKET": os.environ.get("R2_BUCKET", "generated-media"),
        "R2_ENDPOINT": os.environ.get("R2_ENDPOINT", ""),
        "R2_ACCESS_KEY": os.environ.get("R2_ACCESS_KEY", ""),
        "R2_SECRET_KEY": os.environ.get("R2_SECRET_KEY", ""),
    },
)
class MiniMaxH3Ref2VAComfyWorker:
    # --- BEGIN CONTRACT: minimax_h3_ref2va_comfy (generated; run make gen-contracts) ---
    from pydantic import BaseModel

    class Input(BaseModel):
        from typing import Literal as _Literal, Optional as _Optional
        from pydantic import BaseModel as _BaseModel, ConfigDict as _ConfigDict, Field as _Field

        model_config = _ConfigDict(title='MiniMaxH3Ref2VAComfyInput')
        prompt: str = _Field(description='Prompt describing the target shot; reference inputs by tag in connection order, e.g. <Picture 1>, <Video 1>, <Audio 1>.')
        ref_images: list[str] = _Field(default=[], max_length=9, description='Up to 9 reference images as base64 data URLs.')
        ref_videos: list[str] = _Field(default=[], max_length=3, description='Up to 3 reference video clips as base64 data URLs.')
        ref_video_audios: list[str] = _Field(default=[], max_length=3, description='Audio track paired with each reference video (index-aligned with ref_videos).')
        ref_audios: list[str] = _Field(default=[], max_length=3, description='Up to 3 standalone reference audio clips.')
        width: int = _Field(default=1344)
        height: int = _Field(default=768)
        length: int = _Field(default=124)
        steps: int = _Field(default=20)
        seed: _Optional[int] = _Field(default=None)
        ref_image_size: _Literal['match', 'max'] = _Field(default='match')
        scheduler: _Literal['simple', 'beta', 'normal'] = _Field(default='simple')

        @field_validator("ref_audios")
        @classmethod
        def _check_audio_not_alone(cls, v: list[str], info) -> list[str]:
            if v:
                has_visual = bool(info.data.get("ref_images")) or bool(info.data.get("ref_videos"))
                if not has_visual:
                    raise ValueError("reference audio requires at least one reference image or video")
            return v

    # --- END CONTRACT: minimax_h3_ref2va_comfy ---

    _MAX_REF_IMAGES = 9
    _MAX_REF_VIDEOS = 3
    _MAX_REF_AUDIOS = 3
    _MAX_TOTAL_FILES = 12

    def __init__(self):
        import torch.distributed as dist
        dist.is_available = lambda: False
        from runpod_flash import Endpoint

        self.endpoint = Endpoint(
            name="minimax-h3-ref2va-comfy-backend",
            image="ghcr.io/vincezh2000/minimax-h3-comfyui-serverless:cu130",
            gpu=[GpuGroup.ADA_32_PRO],
        )

        self.MODEL_FILES = {
            "unet_name": "minimax_h3_ref2va_pruned_int8_convrot.safetensors",
            "clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
            "vae_video_name": "minimax_h3_video_vae_fp16.safetensors",
            "vae_audio_name": "minimax_h3_audio_vae_fp32.safetensors",
        }

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
                        raise ValueError("reference audio requires at least one reference image or video")
                return v

        self.Input = ValidatedInput

    def _build_workflow(self, req) -> dict:
        workflow = {
            "unet": {
                "class_type": "UNETLoader",
                "inputs": {
                    "unet_name": self.MODEL_FILES["unet_name"],
                    "weight_dtype": "default",
                },
            },
            "clip": {
                "class_type": "CLIPLoader",
                "inputs": {
                    "clip_name": self.MODEL_FILES["clip_name"],
                    "type": "minimax",
                    "device": "default",
                },
            },
            "vae_video": {
                "class_type": "VAELoader",
                "inputs": {"vae_name": self.MODEL_FILES["vae_video_name"]},
            },
            "vae_audio": {
                "class_type": "VAELoader",
                "inputs": {"vae_name": self.MODEL_FILES["vae_audio_name"]},
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

    def _build_images(self, req) -> list[dict]:
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
        steps: int = 20,
        seed: int | None = None,
        ref_image_size: str = "match",
        scheduler: str = "simple",
    ) -> dict:
        import base64
        import os
        import uuid
        import boto3

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
            ref_image_size=ref_image_size,
            scheduler=scheduler,
        )

        payload = {"workflow": self._build_workflow(req)}
        images = self._build_images(req)
        if images:
            payload["images"] = images

        import asyncio

        async def _run():
            return await self.endpoint.runsync(payload, timeout=1800)

        try:
            job = asyncio.run(_run())
        except RuntimeError:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                job = pool.submit(lambda: asyncio.run(_run())).result()

        if getattr(job, "error", None):
            raise RuntimeError(f"job failed: {job.error}")

        output = getattr(job, "output", None) or job
        if not isinstance(output, dict):
            raise RuntimeError(f"unexpected output: {output!r}")

        out_images = output.get("images") or []
        if not out_images:
            raise RuntimeError(f"no video in output: {output}")

        data = out_images[0].get("data")
        if not data:
            raise RuntimeError(f"no data in image result: {out_images[0]}")

        video_bytes = base64.b64decode(data)

        bucket = os.environ.get("R2_BUCKET", "generated-media")
        endpoint_url = os.environ["R2_ENDPOINT"]
        access_key = os.environ["R2_ACCESS_KEY"]
        secret_key = os.environ["R2_SECRET_KEY"]

        key = f"minimax_ref2va_comfy_{uuid.uuid4()}.mp4"
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
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
