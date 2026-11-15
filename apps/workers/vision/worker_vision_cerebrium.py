from __future__ import annotations

import os
import threading

from dist.contract_vision import Input as SmallVisionInput
from shared.worker_vision import do_inference, load_pipeline_lazy, resolve_analyze_prompt

__all__ = ["generate"]

MODEL_CACHE_DIR = "/persistent-storage/worker-vision"
_runtime_lock = threading.Lock()
_model = None
_processor = None
_analyze_prompt = None


def generate(image_base64: str, prompt: str | None = None) -> dict:
    global _model, _processor, _analyze_prompt

    req = SmallVisionInput(image_base64=image_base64, prompt=prompt)
    with _runtime_lock:
        if _model is None:
            _model, _processor, _analyze_prompt = load_pipeline_lazy(
                cache_dir=os.environ.get("VISION_MODEL_CACHE_DIR", MODEL_CACHE_DIR)
            )
        assert _processor is not None and _analyze_prompt is not None
        effective_prompt = resolve_analyze_prompt(_analyze_prompt, req.prompt)
        return do_inference(_model, _processor, effective_prompt, req).model_dump()
