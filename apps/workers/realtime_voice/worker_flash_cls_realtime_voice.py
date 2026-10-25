from __future__ import annotations

from functools import partial

from runpod_flash import Endpoint, GpuGroup
from shared.worker_realtime_voice import (
    IMAGE_PIP_DEPS,
    QWEN_DIR_NAME,
    REFERENCE_VOICES_DIR_NAME,
    WHISPER_DIR_NAME,
    RealtimeVoiceInput,
    do_inference,
    handle_webrtc_audio,
)
from shared.worker_realtime_voice import (
    load_dependencies as shared_load_dependencies,
)

from packages.shared_gpu.guard import run_guarded
from packages.shared_gpu.platform import flash_env, flash_hf_home

HF_HOME_DIR = flash_hf_home()
WHISPER_PATH = f"{HF_HOME_DIR}/{WHISPER_DIR_NAME}"
QWEN_PATH = f"{HF_HOME_DIR}/{QWEN_DIR_NAME}"
REFERENCE_DIR = f"{HF_HOME_DIR}/{REFERENCE_VOICES_DIR_NAME}"


def load_deps() -> dict:
    return shared_load_dependencies(WHISPER_PATH, QWEN_PATH, REFERENCE_DIR)


def generate(models: dict, **kwargs) -> dict:
    return run_guarded(
        RealtimeVoiceInput,
        kwargs,
        partial(do_inference, models),
    )


def generate_webrtc(models: dict, sample_rate: int, audio) -> tuple[int, object]:
    try:
        return handle_webrtc_audio(models, sample_rate, audio)
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


@Endpoint(
    name="realtime-voice-worker",
    gpu=[GpuGroup.AMPERE_16],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env=flash_env(hf_home=HF_HOME_DIR, extra={"HF_HUB_ENABLE_HF_TRANSFER": "1"}),
    dependencies=list(IMAGE_PIP_DEPS),
)
class RealtimeVoiceWorker:
    Input = RealtimeVoiceInput

    def __init__(self):
        self._models = load_deps()

    def generate(self, **kwargs) -> dict:
        return generate(self._models, **kwargs)

    def generate_webrtc(self, sample_rate: int, audio) -> tuple[int, object]:
        return generate_webrtc(self._models, sample_rate, audio)
