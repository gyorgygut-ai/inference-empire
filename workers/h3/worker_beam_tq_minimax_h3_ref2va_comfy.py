from __future__ import annotations

import base64
import subprocess
import time
from typing import TYPE_CHECKING

import requests

from beam import Image, QueueDepthAutoscaler, Volume, task_queue

from workers.h3.generate_minimax_h3_ref2va_comfy import (
    ValidatedRef2VAComfyInput,
    build_payload,
    upload_result,
)

from workers.services.storage.real_r2 import require_storage
if TYPE_CHECKING:
    from workers.services.storage.storage import Storage


CACHE_PATH = "./hf-cache"

image = Image.from_registry(
    "ghcr.io/vincezh2000/minimax-h3-comfyui-serverless:cu130",
).with_envs({
    "HF_HOME": CACHE_PATH,
    "DIFFSYNTH_DOWNLOAD_SOURCE": "huggingface",
    "DIFFSYNTH_MODEL_BASE_PATH": f"{CACHE_PATH}/diffsynth",
    "HF_HUB_ENABLE_HF_TRANSFER": "1",
})


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
def generate(context, storage: Storage, **kwargs) -> dict:
    storage = require_storage(storage)
    t_req = time.time()
    comfy_base_url = context.on_start_value

    try:
        req = ValidatedRef2VAComfyInput(**kwargs)
        n_files = len(req.ref_images) + len(req.ref_videos) + len(req.ref_video_audios) + len(req.ref_audios)
        print(f"[REQ] prompt={req.prompt[:40]}  seed={req.seed}  files={n_files}", flush=True)

        payload = build_payload(req)

        print(f"[GEN] starting ComfyUI job prompt={req.prompt[:40]}", flush=True)
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
        data = base64.b64encode(video_bytes).decode("ascii")

        result = upload_result(storage, video_bytes, data, prefix="minimax_ref2va_comfy")
        print(f"[R2] uploaded key={result.artifact.presigned_url[:60]}", flush=True)

        print(f"[OK] completed in {time.time() - t_req:.1f}s", flush=True)
        return result.model_dump()
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise
