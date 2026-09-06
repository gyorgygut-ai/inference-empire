from __future__ import annotations

import os
from typing import TYPE_CHECKING

from runpod_flash import Endpoint, GpuGroup

from workers.voice._shared_voice_chat import RealtimeVoiceInput, do_inference, load_dependencies

if TYPE_CHECKING:
    from workers.services.storage.storage import Storage


def generate(storage: Storage, **kwargs) -> dict:
    req = RealtimeVoiceInput(**kwargs)
    return do_inference(storage, req).model_dump()


@Endpoint(
    name="realtime-voice-chatterbox-worker",
    gpu=[GpuGroup.AMPERE_16],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env={"HF_HOME": "/runpod-volume/huggingface-cache"},
    dependencies=["torch==2.9.1", "transformers==4.57.6"],
)
class RealtimeVoiceChatterboxWorker:
    Input = RealtimeVoiceInput

    def __init__(self):
        self.storage, = load_dependencies()

    def generate(self, **kwargs) -> dict:
        return generate(self.storage, **kwargs)
