"""Shared business logic for minimax-h3-comfy (ComfyUI backend). No platform imports."""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from packages.media.validation import validate_image_b64

if TYPE_CHECKING:
    from packages.shared_gpu.artifacts.storage import Storage

MODEL_FILES = {
    "unet_name": "minimax_h3_fl2va_pruned_int8_convrot.safetensors",
    "clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
    "vae_video_name": "minimax_h3_video_vae_fp16.safetensors",
    "vae_audio_name": "minimax_h3_audio_vae_fp32.safetensors",
}
FPS = 24

# Single source of truth for ALL provider image pip deps (flash; modal/beam
# use a pinned registry image instead). Worker files must reference this
# list, never inline their own pins.
# Pre-deploy gate: uv run python -c "from apps.h3_comfy._shared_minimax_h3_comfy import IMAGE_PIP_DEPS; print('\n'.join(IMAGE_PIP_DEPS))" | uv pip compile --python-version 3.11 -
IMAGE_PIP_DEPS: list[str] = [
    "boto3==1.43.83",
    "pydantic==2.13.5",
]


def apply_torch_shims() -> None:
    """Patch torch runtime quirks once (remote containers)."""
    import torch.distributed as dist

    try:
        def _dist_unavailable() -> bool:
            return False

        dist.is_available = _dist_unavailable
    except Exception:
        pass


def _load_dotenv() -> None:
    path = Path(__file__).parent.parent / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


class MiniMaxH3ComfyInput(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3ComfyInput")
    prompt: str
    width: int = Field(default=1344)
    height: int = Field(default=768)
    length: int = Field(default=124)
    steps: int = Field(default=20)
    seed: int | None = Field(default=None)
    first_frame: str | None = Field(default=None)
    last_frame: str | None = Field(default=None)

    @field_validator("first_frame", "last_frame")
    @classmethod
    def _check_frame(cls, v: str | None, info: ValidationInfo) -> str | None:
        if v is None:
            return None
        return validate_image_b64(v, info.field_name)

class Artifact(BaseModel):
    model_config = ConfigDict(title="Artifact")
    presigned_url: str

class MiniMaxH3ComfyOutput(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3ComfyOutput")
    artifact: Artifact

def build_workflow(req: MiniMaxH3ComfyInput) -> dict:
    workflow = {
        "unet": {"class_type": "UNETLoader", "inputs": {"unet_name": MODEL_FILES["unet_name"], "weight_dtype": "default"}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": MODEL_FILES["clip_name"], "type": "minimax", "device": "default"}},
        "vae_video": {"class_type": "VAELoader", "inputs": {"vae_name": MODEL_FILES["vae_video_name"]}},
        "vae_audio": {"class_type": "VAELoader", "inputs": {"vae_name": MODEL_FILES["vae_audio_name"]}},
        "cond": {"class_type": "MiniMaxH3ImageToVideo", "inputs": {
            "clip": ["clip", 0], "vae": ["vae_video", 0],
            "prompt": req.prompt, "width": req.width, "height": req.height, "length": req.length}},
        "noise": {"class_type": "RandomNoise", "inputs": {"noise_seed": req.seed if req.seed is not None else 42}},
        "guider": {"class_type": "BasicGuider", "inputs": {"model": ["unet", 0], "conditioning": ["cond", 0]}},
        "sampler_select": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
        "sigmas": {"class_type": "BasicScheduler", "inputs": {"model": ["unet", 0], "scheduler": "simple", "steps": req.steps, "denoise": 1.0}},
        "sample": {"class_type": "SamplerCustomAdvanced", "inputs": {
            "noise": ["noise", 0], "guider": ["guider", 0], "sampler": ["sampler_select", 0],
            "sigmas": ["sigmas", 0], "latent_image": ["cond", 1]}},
        "decode_video": {"class_type": "VAEDecode", "inputs": {"samples": ["sample", 0], "vae": ["vae_video", 0]}},
        "decode_audio": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["sample", 0], "vae": ["vae_audio", 0]}},
        "video": {"class_type": "CreateVideo", "inputs": {"images": ["decode_video", 0], "fps": FPS, "audio": ["decode_audio", 0]}},
        "save": {"class_type": "SaveVideo", "inputs": {"video": ["video", 0], "filename_prefix": "video/MiniMax_H3", "format": "auto", "codec": "auto"}},
    }
    if req.first_frame:
        workflow["load_first"] = {"class_type": "LoadImage", "inputs": {"image": "first_frame.png"}}
        workflow["cond"]["inputs"]["first_frame"] = ["load_first", 0]
    if req.last_frame:
        workflow["load_last"] = {"class_type": "LoadImage", "inputs": {"image": "last_frame.png"}}
        workflow["cond"]["inputs"]["last_frame"] = ["load_last", 0]
    return workflow

def build_images(req: MiniMaxH3ComfyInput) -> list[dict]:
    images = []
    if req.first_frame:
        images.append({"name": "first_frame.png", "image": f"data:image/png;base64,{req.first_frame}"})
    if req.last_frame:
        images.append({"name": "last_frame.png", "image": f"data:image/png;base64,{req.last_frame}"})
    return images

def build_payload(req: MiniMaxH3ComfyInput) -> dict:
    payload = {"workflow": build_workflow(req)}
    images = build_images(req)
    if images:
        payload["images"] = images
    return payload

def parse_output(output) -> bytes:
    """Returns video_bytes. Raises RuntimeError on malformed output."""
    import base64

    if not isinstance(output, dict):
        raise TypeError(f"unexpected output: {output!r}")
    out_images = output.get("images") or []
    if not out_images:
        raise RuntimeError(f"no video in output: {output}")
    data = out_images[0].get("data")
    if not data:
        raise RuntimeError(f"no data in image result: {out_images[0]}")
    return base64.b64decode(data)

def upload_result(storage: Storage, video_bytes: bytes, prefix: str = "minimax_comfy") -> MiniMaxH3ComfyOutput:
    key = f"{prefix}_{uuid.uuid4()}.mp4"
    storage.put(key, video_bytes)
    presigned_url = storage.presigned_url(key)
    print(f"[R2] uploaded key={presigned_url[:60]}", flush=True)

    return MiniMaxH3ComfyOutput(artifact=Artifact(presigned_url=presigned_url))

def run_comfy_endpoint(endpoint, payload, timeout: int = 1800):
    """Submit payload to a ComfyUI flash endpoint, tolerating a running loop."""
    import asyncio
    import concurrent.futures

    async def _run():
        return await endpoint.runsync(payload, timeout=timeout)

    try:
        return asyncio.run(_run())
    except RuntimeError:
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(lambda: asyncio.run(_run())).result()

POLL_INTERVAL_S = 5
POLL_BUDGET_S = 3600
HEARTBEAT_S = 60


def _upload_frame(comfy_base_url: str, name: str, raw_b64: str) -> None:
    """Upload a validated raw-base64 frame so LoadImage nodes can find it."""
    import base64

    import requests

    blob = base64.b64decode(raw_b64)
    files = {"image": (name, blob, "image/png")}
    r = requests.post(
        f"{comfy_base_url}/upload/image",
        files=files,
        data={"overwrite": "true"},
        timeout=60,
    )
    try:
        r.raise_for_status()
    except requests.HTTPError as exc:
        raise RuntimeError(f"ComfyUI /upload/image for {name} failed: {exc}: {r.text[:2000]}") from exc
    print(f"[GEN] uploaded frame {name} ({len(blob)} bytes)", flush=True)


_QUEUE_SHAPE_LOGGED = False


def _read_server_log_tail(max_bytes: int = 65536) -> str | None:
    """Read the tail of the ComfyUI server log file (if the worker captures one)."""
    try:
        with open("/tmp/comfy_server.log", "rb") as fh:
            fh.seek(0, 2)
            fh.seek(max(0, fh.tell() - max_bytes))
            return fh.read().decode("utf-8", "replace")
    except OSError:
        return None


def _dump_server_log(lines: int = 40) -> None:
    """Tail the ComfyUI server log file (if the worker captures one)."""
    text = _read_server_log_tail()
    if text is None:
        print("[COMFY-SERVER] no server log", flush=True)
        return
    print("[COMFY-SERVER] last log lines:", flush=True)
    for line in text.splitlines()[-lines:]:
        print(f"[COMFY-SERVER] {line}", flush=True)


def _video_from_server_log() -> tuple[str, str, str] | None:
    """Parse the most recent saved-video (filename, subfolder, type) from the server log.

    Some SaveVideo-style nodes persist the file but return nothing in the
    history entry, so the log's save line is the only record of the name.
    """
    import re

    text = _read_server_log_tail()
    if not text:
        return None
    hits = re.findall(r"[Ss]av(?:ed?|ing) (?:video )?(?:to )?['\"]?([^\s'\"]+\.(?:mp4|webm|mov|gif))['\"]?", text)
    if not hits:
        return None
    path = hits[-1]
    filename = path.rsplit("/", 1)[-1]
    subfolder = ""
    if "/output/" in path:
        subfolder = path.split("/output/", 1)[1].rsplit("/", 1)[0]
        if subfolder == filename:
            subfolder = ""
    return filename, subfolder, "output"


def _queue_position(comfy_base_url: str, prompt_id: str) -> str:
    """Best-effort running/queued position for heartbeat lines."""
    import requests

    global _QUEUE_SHAPE_LOGGED
    try:
        q = requests.get(f"{comfy_base_url}/queue", timeout=10).json()
        if not _QUEUE_SHAPE_LOGGED:
            _QUEUE_SHAPE_LOGGED = True
            print(
                f"[COMFY] queue shape keys={sorted(q.keys())} "
                f"running0={str(q.get('queue_running', [])[:1])[:300]} "
                f"pending0={str(q.get('queue_pending', [])[:1])[:300]}",
                flush=True,
            )
        running = [e[1] for e in q.get("queue_running", []) if len(e) > 1]
        pending = [e[1] for e in q.get("queue_pending", []) if len(e) > 1]
        if prompt_id in running:
            return "running"
        if prompt_id in pending:
            return f"queued #{pending.index(prompt_id) + 1}/{len(pending)}"
        return "finishing"
    except Exception:
        return "unknown"


def _comfy_error(entry: dict) -> str | None:
    """Extract node error text from a history entry, or None if not failed."""
    status = entry.get("status") or {}
    if status.get("status_str") == "error":
        msgs = status.get("messages") or []
        errors = [
            str(m[1].get("exception_message", m[1]))
            for m in msgs
            if isinstance(m, (list, tuple)) and len(m) > 1
            and m[0] in ("execution_error", "execution_interrupted")
            and isinstance(m[1], dict)
        ]
        detail = "; ".join(errors) if errors else str(msgs)
        return f"ComfyUI job failed: {detail}"
    return None


def _run_local(comfy_base_url: str, req: MiniMaxH3ComfyInput) -> bytes:
    """Submit + poll (up to POLL_BUDGET_S) + fetch. Returns video_bytes."""
    import time

    import requests

    print(f"[REQ] prompt={req.prompt[:40]}", flush=True)
    workflow = build_workflow(req)

    if req.first_frame:
        _upload_frame(comfy_base_url, "first_frame.png", req.first_frame)
    if req.last_frame:
        _upload_frame(comfy_base_url, "last_frame.png", req.last_frame)

    t_gen = time.time()
    r = requests.post(f"{comfy_base_url}/prompt", json={"prompt": workflow}, timeout=30)
    try:
        r.raise_for_status()
    except requests.HTTPError as exc:
        # ComfyUI's 400 body names the rejecting node (node_errors) — never drop it.
        raise RuntimeError(f"ComfyUI /prompt rejected workflow: {exc}: {r.text[:2000]}") from exc
    prompt_id = r.json()["prompt_id"]
    print(f"[GEN] starting ComfyUI job prompt={req.prompt[:40]} prompt_id={prompt_id}", flush=True)

    video_info = None
    attempt = 0
    last_beat = t_gen
    last_summary = "no-entry"
    deadline = t_gen + POLL_BUDGET_S
    while time.time() < deadline:
        attempt += 1
        try:
            r = requests.get(f"{comfy_base_url}/history/{prompt_id}", timeout=10)
            r.raise_for_status()
            history = r.json()
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError, ValueError) as e:
            print(
                f"[COMFY] poll {attempt} transient error: {type(e).__name__}: {e}",
                flush=True,
            )
            time.sleep(POLL_INTERVAL_S)
            continue
        entry = history.get(prompt_id)
        if entry is not None:
            err = _comfy_error(entry)
            if err is not None:
                _dump_server_log()
                raise RuntimeError(f"ComfyUI job {prompt_id}: {err}")
            outputs = entry.get("outputs") or {}
            status_str = (entry.get("status") or {}).get("status_str")
            save_node = outputs.get("save", {})
            last_summary = f"status={status_str} outputs={sorted(outputs.keys())} save_keys={sorted(save_node.keys())}"
            # SaveVideo here returns a PreviewImage-style payload (images + animated flag).
            video_info = (
                save_node.get("videos")
                or save_node.get("gifs")
                or save_node.get("images")
                or [None]
            )[0]
            if video_info:
                break
            if status_str == "success" and save_node is not None:
                # Node persisted the file but returned no handle — resolve via server log.
                logged = _video_from_server_log()
                if logged is not None:
                    filename, subfolder, typ = logged
                    print(f"[GEN] save node empty, server log points at {subfolder}/{filename}", flush=True)
                    video_info = {"filename": filename, "subfolder": subfolder, "type": typ}
                    break
        now = time.time()
        if now - last_beat >= HEARTBEAT_S:
            pos = _queue_position(comfy_base_url, prompt_id)
            print(f"[COMFY] still running {now - t_gen:.0f}s ({pos}) history={last_summary}", flush=True)
            last_beat = now
        time.sleep(POLL_INTERVAL_S)

    if video_info is None:
        _dump_server_log()
        raise RuntimeError(f"ComfyUI job {prompt_id} did not complete within {POLL_BUDGET_S}s")

    print(f"[GEN] ComfyUI job done in {time.time() - t_gen:.1f}s", flush=True)
    video_url = (
        f"{comfy_base_url}/view?filename={video_info['filename']}"
        f"&subfolder={video_info.get('subfolder', '')}&type={video_info.get('type', 'output')}"
    )
    r = requests.get(video_url, timeout=60)
    r.raise_for_status()
    video_bytes = r.content
    if not video_bytes:
        raise RuntimeError(f"ComfyUI job {prompt_id}: empty video at {video_url}")

    return video_bytes

def _run_flash(endpoint, req: MiniMaxH3ComfyInput) -> bytes:
    """Submit via flash endpoint. Returns video_bytes."""
    import time

    print(f"[REQ] prompt={req.prompt[:40]}", flush=True)
    payload = build_payload(req)

    print(f"[GEN] starting ComfyUI job prompt={req.prompt[:40]}", flush=True)
    t_gen = time.time()
    job = run_comfy_endpoint(endpoint, payload)
    print(f"[GEN] ComfyUI job done in {time.time() - t_gen:.1f}s", flush=True)

    if getattr(job, "error", None):
        raise RuntimeError(f"job failed: {job.error}")

    output = getattr(job, "output", None) or job
    video_bytes = parse_output(output)

    return video_bytes

def do_inference(backend, storage: Storage, req: MiniMaxH3ComfyInput) -> MiniMaxH3ComfyOutput:
    """Local (base_url str) and flash (endpoint) paths converge here. Testable via DI."""
    import time

    t_req = time.time()
    if isinstance(backend, str):
        video_bytes = _run_local(backend, req)
    else:
        video_bytes = _run_flash(backend, req)

    result = upload_result(storage, video_bytes, prefix="minimax_comfy")
    print(f"[R2] uploaded key={result.artifact.presigned_url[:60]}", flush=True)

    print(f"[OK] completed in {time.time() - t_req:.1f}s", flush=True)
    return result
