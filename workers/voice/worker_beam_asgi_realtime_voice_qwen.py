"""Single Beam.cloud @asgi voice worker.

Exposes an OpenAI Realtime-compatible WebSocket at ``/v1/realtime``. All three
models (Whisper STT, Qwen2.5-3B-Instruct LLM, Chatterbox TTS) plus Silero VAD are loaded
once in ``on_start`` and reused across sessions (PLAN.md §1, §3).
"""

from __future__ import annotations

import os
import time

from beam import Image, QueueDepthAutoscaler, Volume, asgi

VOLUME_NAME = "models"
MOUNT_PATH = "/volumes/models"

WHISPER_PATH = f"{MOUNT_PATH}/whisper-fw"
QWEN_PATH = f"{MOUNT_PATH}/qwen3-4b"

ROOT = os.path.dirname(os.path.abspath(__file__))
VOICES_JSON = os.path.join(ROOT, "voices", "reference_voices", "voices.json")

image = (
    Image(
        base_image="nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04",
        python_version="python3.10",
    )
    .add_commands(["apt-get update && apt-get install -y ffmpeg"])
    .add_python_packages(
        [
            "fastapi",
            "uvicorn[standard]",
            "numpy",
            "setuptools",
            "soundfile",
            "faster-whisper",
            "ctranslate2==4.4.0",
            "transformers>=4.57,<5",
            "torch",
            "bitsandbytes",
            "chatterbox-tts==0.1.7",
            "librosa>=0.10",
            "silero-vad",
            "huggingface_hub[hf-transfer]>=0.30",
            "hf_xet",
        ]
    )
    .with_envs("HF_HUB_ENABLE_HF_TRANSFER=1", "HF_HOME=/volumes/models/.hf_cache")
)

volume = Volume(name=VOLUME_NAME, mount_path=MOUNT_PATH)


def ensure_model(local_dir: str, repo_id: str) -> None:
    """Download ``repo_id`` into ``local_dir`` on first boot (cold start).

    Skips the download if the directory is already populated, so later boots
    load straight from the Volume.
    """
    if os.path.isdir(local_dir) and any(os.scandir(local_dir)):
        return
    from huggingface_hub import snapshot_download

    os.makedirs(local_dir, exist_ok=True)
    print(f"[INIT] downloading {repo_id} -> {local_dir}")
    snapshot_download(
        repo_id=repo_id,
        local_dir=local_dir,
        local_dir_use_symlinks=False,
    )


def ensure_whisper(local_dir: str) -> str:
    """Download faster-whisper (large-v3) via the proven Beam recipe.

    Uses faster_whisper.download_model with hf-transfer, caching into the
    Volume so later boots skip the download. Mirrors beam-cloud/examples
    audio_and_transcription/faster_whisper. Returns the model directory.
    """
    if os.path.isdir(local_dir) and any(os.scandir(local_dir)):
        return local_dir
    from faster_whisper import download_model

    os.makedirs(local_dir, exist_ok=True)
    print(f"[INIT] downloading faster-whisper-large-v3 -> {local_dir}")
    return download_model("large-v3", cache_dir=local_dir)


def load_models():
    t0 = time.time()
    boot_log = os.path.join(MOUNT_PATH, "worker_boot_error.log")
    try:
        # Activate the Xet download backend (installed in the image but must be
        # imported to register it, otherwise Xet-stored weights 404).
        import hf_xet  # noqa: F401

        whisper_dir = ensure_whisper(WHISPER_PATH)
        ensure_model(QWEN_PATH, "Qwen/Qwen2.5-3B-Instruct")

        from handlers.chatterbox_tts import Chatterbox
        from handlers.llm import QwenLLM
        from handlers.stt import WhisperSTT
        from realtime.vad import SileroVAD

        models = {
            # Chatterbox is the primary (and currently only) TTS: it voices
            # replies in the selected reference timbre. It downloads its weights
            # on demand (cold start) if not already cached.
            "tts": Chatterbox(device="cuda").load(),
            "stt": WhisperSTT(whisper_dir).load(),
            "llm": QwenLLM(QWEN_PATH).load(),
            "vad": SileroVAD().load(),
        }
        print(f"[INIT] loaded all models in {time.time() - t0:.1f}s")
        return models
    except Exception:
        import traceback

        with open(boot_log, "w") as f:
            f.write(traceback.format_exc())
        raise


def build_app(models: dict, voices_config: dict | None, default_voice: str = "GutAI"):
    """Build the FastAPI app exposing ``/v1/realtime`` (see ``realtime/app.py``)."""
    from realtime.app import build_app as _build

    return _build(models, voices_config, default_voice)


@asgi(
    name="voice-worker",
    image=image,
    volumes=[volume],
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
    autoscaler=QueueDepthAutoscaler(max_containers=1, min_containers=0),
)
def worker(context):
    from handlers.voices_config import load_voices_config

    models = context.on_start_value
    voices_config = load_voices_config(VOICES_JSON)
    return build_app(models, voices_config)
