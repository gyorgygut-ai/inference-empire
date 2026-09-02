import os
import time
import uuid

import boto3
from runpod_flash import Endpoint, GpuGroup, PodTemplate


@Endpoint(
    name="minimax-h3-comfy-worker",
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
class MiniMaxH3ComfyWorker:
    # --- BEGIN CONTRACT: minimax_h3_comfy (generated; run make gen-contracts) ---
    from pydantic import BaseModel

    class Input(BaseModel):
        from typing import Literal as _Literal, Optional as _Optional
        from pydantic import BaseModel as _BaseModel, ConfigDict as _ConfigDict, Field as _Field

        model_config = _ConfigDict(title='MiniMaxH3ComfyInput')
        prompt: str
        width: int = _Field(default=1344)
        height: int = _Field(default=768)
        length: int = _Field(default=124)
        steps: int = _Field(default=20)
        seed: _Optional[int] = _Field(default=None)
        first_frame: _Optional[str] = _Field(default=None)
        last_frame: _Optional[str] = _Field(default=None)
    # --- END CONTRACT: minimax_h3_comfy ---

    def __init__(self):
        import torch.distributed as dist
        dist.is_available = lambda: False
        from runpod_flash import Endpoint

        self.endpoint = Endpoint(
            name="minimax-h3-comfy-backend",
            image="ghcr.io/vincezh2000/minimax-h3-comfyui-serverless:cu130",
            gpu=[GpuGroup.ADA_32_PRO],
        )

        self.MODEL_FILES = {
            "unet_name": "minimax_h3_fl2va_pruned_int8_convrot.safetensors",
            "clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
            "vae_video_name": "minimax_h3_video_vae_fp16.safetensors",
            "vae_audio_name": "minimax_h3_audio_vae_fp32.safetensors",
        }

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
                "class_type": "MiniMaxH3ImageToVideo",
                "inputs": {
                    "clip": ["clip", 0],
                    "vae": ["vae_video", 0],
                    "prompt": req.prompt,
                    "width": req.width,
                    "height": req.height,
                    "length": req.length,
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
                    "scheduler": "simple",
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
                    "filename_prefix": "video/MiniMax_H3",
                    "format": "auto",
                    "codec": "auto",
                },
            },
        }

        if req.first_frame:
            workflow["load_first"] = {
                "class_type": "LoadImage",
                "inputs": {"image": "first_frame.png"},
            }
            workflow["cond"]["inputs"]["first_frame"] = ["load_first", 0]

        if req.last_frame:
            workflow["load_last"] = {
                "class_type": "LoadImage",
                "inputs": {"image": "last_frame.png"},
            }
            workflow["cond"]["inputs"]["last_frame"] = ["load_last", 0]

        return workflow

    def _build_images(self, req) -> list[dict]:
        images = []
        if req.first_frame:
            images.append(
                {"name": "first_frame.png", "image": f"data:image/png;base64,{req.first_frame}"}
            )
        if req.last_frame:
            images.append(
                {"name": "last_frame.png", "image": f"data:image/png;base64,{req.last_frame}"}
            )
        return images

    def generate(
        self,
        prompt: str,
        width: int = 1344,
        height: int = 768,
        length: int = 124,
        steps: int = 20,
        seed: int | None = None,
        first_frame: str | None = None,
        last_frame: str | None = None,
    ) -> dict:
        import base64
        import os
        import uuid
        import boto3

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

        payload = {"workflow": self._build_workflow(req)}
        images = self._build_images(req)
        if images:
            payload["images"] = images

        import asyncio

        # Since generate is a regular `def` method in class-based workers (Pattern C),
        # but endpoint runsync is async, we can run it via asyncio.run or similar.
        async def _run():
            return await self.endpoint.runsync(payload, timeout=1800)

        try:
            job = asyncio.run(_run())
        except RuntimeError:
            # If an event loop is already running in this thread:
            # create a new loop in a background thread or similar, or runsync
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

        key = f"minimax_comfy_{uuid.uuid4()}.mp4"
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
