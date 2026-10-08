from __future__ import annotations

from functools import partial

from runpod_flash import Endpoint, GpuGroup

from packages.realtime_voice.shared import (
    IMAGE_PIP_DEPS,
    QWEN_DIR_NAME,
    WHISPER_DIR_NAME,
    RealtimeVoiceInput,
    do_inference,
    handle_webrtc_audio,
)
from packages.realtime_voice.shared import (
    load_dependencies as shared_load_dependencies,
)
from packages.shared_gpu.guard import new_lock, run_guarded
from packages.shared_gpu.platform import flash_env, flash_hf_home

HF_HOME_DIR = flash_hf_home()
WHISPER_PATH = f"{HF_HOME_DIR}/{WHISPER_DIR_NAME}"
QWEN_PATH = f"{HF_HOME_DIR}/{QWEN_DIR_NAME}"
REFERENCE_DIR = "/runpod-volume/models/reference_voices"


def load_models() -> dict:
    """Flash loader: delegates to shared single-source loader."""
    return shared_load_dependencies(WHISPER_PATH, QWEN_PATH, REFERENCE_DIR)


def load_dependencies() -> dict:
    """Flash entrypoint alias for test-mocking parity with Beam/Modal."""
    return load_models()


def generate(models: dict, **kwargs) -> dict:
    return run_guarded(RealtimeVoiceInput, kwargs, partial(do_inference, models))


def generate_webrtc(models: dict, sample_rate: int, audio) -> tuple[int, object]:
    try:
        return handle_webrtc_audio(models, sample_rate, audio)
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


@Endpoint(
    name="realtime-voice-qwen-worker",
    gpu=[
        GpuGroup.AMPERE_16,
    ],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env=flash_env(hf_home=HF_HOME_DIR, extra={"HF_HUB_ENABLE_HF_TRANSFER": "1"}),
    dependencies=list(IMAGE_PIP_DEPS),
)
class RealtimeVoiceWorker:
    Input = RealtimeVoiceInput

    def __init__(self):
        self._models = None
        self._lock = new_lock()

    def _load_models(self) -> dict:
        return load_models()

    def generate(self, **kwargs) -> dict:
        if self._models is None:
            with self._lock:
                if self._models is None:
                    self._models = self._load_models()

        with self._lock:
            return generate(self._models, **kwargs)

    def generate_webrtc(self, sample_rate: int, audio) -> tuple[int, object]:
        """WebRTC parity with shared handler (Beam/Modal ASGI path)."""
        if self._models is None:
            with self._lock:
                if self._models is None:
                    self._models = self._load_models()
        with self._lock:
            return generate_webrtc(self._models, sample_rate, audio)
