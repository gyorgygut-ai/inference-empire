from __future__ import annotations

import importlib.util
import os
import threading
import time

try:
    from beam import Image, QueueDepthAutoscaler, Volume, asgi
except Exception:  # unit tests without beam credentials
    from apps.conftest import _Fluent as Image
    from apps.conftest import _Fluent as QueueDepthAutoscaler
    from apps.conftest import _Fluent as Volume

    def asgi(**kwargs):
        def deco(fn):
            return fn

        return deco


def _load_shared():
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "_shared_realtime_voice_qwen.py"
    )
    spec = importlib.util.spec_from_file_location("_shared_realtime_voice_qwen", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_shared = _load_shared()
IMAGE_PIP_DEPS = _shared.IMAGE_PIP_DEPS
CHATTERBOX_TTS_NO_DEPS = _shared.CHATTERBOX_TTS_NO_DEPS
RealtimeVoiceInput = _shared.RealtimeVoiceInput
build_app = _shared.build_app
do_inference = _shared.do_inference

VOLUME_NAME = "models"
MOUNT_PATH = "/volumes/models"
WHISPER_PATH = f"{MOUNT_PATH}/whisper-fw"
QWEN_PATH = f"{MOUNT_PATH}/qwen3-4b"

image = (
    Image(
        base_image="nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04",
        python_version="python3.10",
    )
    .add_commands(["apt-get update && apt-get install -y ffmpeg"])
    .add_python_packages(list(IMAGE_PIP_DEPS))
    .add_commands([f"pip install --no-deps {CHATTERBOX_TTS_NO_DEPS}"])
    .with_envs({"HF_HUB_ENABLE_HF_TRANSFER": "1", "HF_HOME": "/volumes/models/.hf_cache"})
)

volume = Volume(name=VOLUME_NAME, mount_path=MOUNT_PATH)

_INFERENCE_LOCK = threading.Lock()


def ensure_model(local_dir: str, repo_id: str) -> None:
    if os.path.isdir(local_dir) and any(os.scandir(local_dir)):
        return
    from huggingface_hub import snapshot_download

    os.makedirs(local_dir, exist_ok=True)
    print(f"[INIT] downloading {repo_id} -> {local_dir}", flush=True)
    snapshot_download(repo_id=repo_id, local_dir=local_dir, local_dir_use_symlinks=False)


def ensure_whisper(local_dir: str) -> str:
    if os.path.isdir(local_dir) and any(os.scandir(local_dir)):
        return local_dir
    from faster_whisper import download_model

    os.makedirs(local_dir, exist_ok=True)
    print("[INIT] downloading faster-whisper-large-v3", flush=True)
    return download_model("large-v3", cache_dir=local_dir)


def load_models():
    import torch.distributed as dist

    def _dist_unavailable() -> bool:
        return False

    setattr(dist, "is_available", _dist_unavailable)
    import hf_xet  # noqa: F401

    t0 = time.time()
    try:
        whisper_dir = ensure_whisper(WHISPER_PATH)
        ensure_model(QWEN_PATH, "Qwen/Qwen2.5-3B-Instruct")
        models = {
            "stt": _shared.WhisperSTT(whisper_dir).load(),
            "llm": _shared.QwenLLM(QWEN_PATH).load(),
            "tts": _shared.ChatterboxTTS().load(),
        }
        print(f"[INIT] loaded all models in {time.time() - t0:.1f}s", flush=True)
        return models
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise


def load_dependencies():
    return load_models()


def generate(models: dict, **kwargs) -> dict:
    req = RealtimeVoiceInput(**kwargs)
    try:
        with _INFERENCE_LOCK:
            return do_inference(models, req).model_dump()
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


@asgi(
    name="realtime-voice-qwen-worker",
    image=image,
    volumes=[volume],  # ty: ignore[invalid-argument-type]
    on_start=load_models,
    gpu="RTX4090",
    cpu=4,
    memory="32Gi",
    concurrent_requests=4,
    keep_warm_seconds=10,
    timeout=-1,
    authorized=True,
    checkpoint_enabled=True,
    secrets=["HF_TOKEN"],
    autoscaler=QueueDepthAutoscaler(max_containers=1, min_containers=0),  # ty: ignore[invalid-argument-type]
)
def worker(context):
    models = context.on_start_value
    return build_app(models)
