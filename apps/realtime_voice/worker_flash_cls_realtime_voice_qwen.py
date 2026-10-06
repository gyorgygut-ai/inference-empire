from __future__ import annotations

import os
import threading
import time
from runpod_flash import Endpoint, GpuGroup

from apps.realtime_voice._shared_realtime_voice_qwen import (
    IMAGE_PIP_DEPS,
    RealtimeVoiceInput,
    do_inference,
    WhisperSTT,
    QwenLLM,
    ChatterboxTTS,
)

HF_HOME = os.getenv("HF_HOME", "/runpod-volume/huggingface-cache")
WHISPER_PATH = f"{HF_HOME}/whisper-fw"
QWEN_PATH = f"{HF_HOME}/qwen3-4b"
REFERENCE_DIR = "/runpod-volume/models/reference_voices"


def _patch_torch_dist() -> None:
    import torch.distributed as dist

    def _dist_unavailable() -> bool:
        return False

    setattr(dist, "is_available", _dist_unavailable)


def ensure_whisper(local_dir: str) -> str:
    if os.path.isdir(local_dir) and any(os.scandir(local_dir)):
        return local_dir
    from faster_whisper import download_model

    os.makedirs(local_dir, exist_ok=True)
    print("[INIT] downloading faster-whisper-large-v3", flush=True)
    return download_model("large-v3", cache_dir=local_dir)


def ensure_model(local_dir: str, repo_id: str) -> None:
    if os.path.isdir(local_dir) and any(os.scandir(local_dir)):
        return
    from huggingface_hub import snapshot_download

    os.makedirs(local_dir, exist_ok=True)
    print(f"[INIT] downloading {repo_id} -> {local_dir}", flush=True)
    snapshot_download(repo_id=repo_id, local_dir=local_dir, local_dir_use_symlinks=False)


@Endpoint(
    name="realtime-voice-qwen-worker",
    gpu=[
        GpuGroup.AMPERE_16,
    ],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env={
        "HF_HOME": HF_HOME,
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
    },
    dependencies=list(IMAGE_PIP_DEPS),
)
class RealtimeVoiceWorker:
    Input = RealtimeVoiceInput

    def __init__(self):
        self._models = None
        self._lock = threading.Lock()

    def _load_models(self) -> dict:
        _patch_torch_dist()
        t0 = time.time()
        try:
            whisper_dir = ensure_whisper(WHISPER_PATH)
            ensure_model(QWEN_PATH, "Qwen/Qwen2.5-3B-Instruct")
            models = {
                "stt": WhisperSTT(whisper_dir).load(),
                "llm": QwenLLM(QWEN_PATH).load(),
                "tts": ChatterboxTTS(reference_dir=REFERENCE_DIR).load(),
            }
            print(f"[INIT] loaded all models in {time.time() - t0:.1f}s", flush=True)
            return models
        except Exception as e:
            print(f"[ERR] load_models failed: {type(e).__name__}: {e}", flush=True)
            raise

    def generate(self, **kwargs) -> dict:
        if self._models is None:
            with self._lock:
                if self._models is None:
                    self._models = self._load_models()

        req = RealtimeVoiceInput(**kwargs)
        try:
            with self._lock:
                return do_inference(self._models, req).model_dump()
        except Exception as e:
            print(f"[ERR] {type(e).__name__}: {e}", flush=True)
            raise RuntimeError(f"inference failed: {e}") from e
