from __future__ import annotations

import importlib.util
import os
import threading
from pathlib import Path

import modal


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
load_dependencies = _shared.load_dependencies

app = modal.App("realtime-voice-qwen-worker")

_INFERENCE_LOCK = threading.Lock()

dotenv_secret = modal.Secret.from_dotenv(str(Path(__file__).parent.parent.parent / ".env"))
hf_cache_vol = modal.Volume.from_name("hf-cache", create_if_missing=True)
MODEL_MOUNT = "/root/.cache/huggingface"

image = (
    modal.Image.debian_slim(python_version="3.10")
    .apt_install("ffmpeg", "libsndfile1")
    .pip_install(*IMAGE_PIP_DEPS)
    .run_commands(f"pip install --no-deps {CHATTERBOX_TTS_NO_DEPS}")
    .env({"HF_HOME": MODEL_MOUNT, "HF_HUB_ENABLE_HF_TRANSFER": "1"})
    .add_local_python_source("apps", "apps")
    .add_local_python_source("packages", "packages")
)


def generate(models: dict, **kwargs) -> dict:
    req = RealtimeVoiceInput(**kwargs)
    try:
        with _INFERENCE_LOCK:
            return do_inference(models, req).model_dump()
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


@app.cls(
    image=image,
    gpu="L4",
    secrets=[dotenv_secret],
    volumes={MODEL_MOUNT: hf_cache_vol},
    timeout=3600,
    memory=32768,
    scaledown_window=60,
    max_containers=1,
)
class RealtimeVoiceWorker:
    @modal.enter()
    def load(self):
        import torch.distributed as dist

        def _dist_unavailable() -> bool:
            return False

        setattr(dist, "is_available", _dist_unavailable)

        print("[INIT] loading realtime-voice-qwen models", flush=True)
        self.models = {
            "stt": _shared.WhisperSTT(f"{MODEL_MOUNT}/whisper-fw").load(),
            "llm": _shared.QwenLLM(f"{MODEL_MOUNT}/qwen3-4b").load(),
            "tts": _shared.ChatterboxTTS().load(),
        }
        print("[INIT] models loaded", flush=True)

    @modal.method()
    def generate(self, **kwargs) -> dict:
        return generate(self.models, **kwargs)


@app.function(
    image=image,
    volumes={MODEL_MOUNT: hf_cache_vol},
    timeout=3600,
    scaledown_window=60,
    max_containers=1,
)
@modal.concurrent(max_inputs=10)
@modal.asgi_app()
def web():
    models = load_dependencies()
    if not models:
        models = {
            "stt": _shared.WhisperSTT(f"{MODEL_MOUNT}/whisper-fw").load(),
            "llm": _shared.QwenLLM(f"{MODEL_MOUNT}/qwen3-4b").load(),
            "tts": _shared.ChatterboxTTS().load(),
        }
    return build_app(models)
