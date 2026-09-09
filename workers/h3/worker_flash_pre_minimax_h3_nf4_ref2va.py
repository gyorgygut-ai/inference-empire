from __future__ import annotations

from typing import TYPE_CHECKING

from runpod_flash import Endpoint, GpuGroup

from workers.h3._shared_minimax_h3_nf4_ref2va import (
    IMAGE_PIP_DEPS,
    MiniMaxH3Nf4Ref2vaInput,
    do_inference,
    load_dependencies,
)

if TYPE_CHECKING:
    from workers.services.storage.storage import Storage


def generate(storage: Storage, pipe, write_video_audio, **kwargs) -> dict:
    req = MiniMaxH3Nf4Ref2vaInput(**kwargs)
    try:
        return do_inference(pipe, write_video_audio, storage, req).model_dump()
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


@Endpoint(
    name="minimax-h3-nf4-ref2va-worker",
    gpu=[
        GpuGroup.AMPERE_48,
    ],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env={
        "HF_HOME": "/runpod-volume/huggingface-cache",
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
        "DIFFSYNTH_DOWNLOAD_SOURCE": "HuggingFace",
    },
    dependencies=list(IMAGE_PIP_DEPS),
)
class MiniMaxH3Ref2vaWorker:
    Input = MiniMaxH3Nf4Ref2vaInput

    def __init__(self):
        self._loaded = False
        self.storage = None
        self.pipe = None
        self.write_video_audio = None

    def generate(self, **kwargs) -> dict:
        if not self._loaded:
            self.storage, self.pipe, self.write_video_audio = load_dependencies()
            self._loaded = True
        return generate(self.storage, self.pipe, self.write_video_audio, **kwargs)
