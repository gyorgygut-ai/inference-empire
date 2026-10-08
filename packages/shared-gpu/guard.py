"""One guarded inference entrypoint for all workers. No platform imports."""
from __future__ import annotations

import threading
from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel

_INFERENCE_LOCK = threading.Lock()

TInput = TypeVar("TInput", bound=BaseModel)


def new_lock() -> threading.Lock:
    """Fresh lock for load guards. Inference serialization uses run_guarded."""
    return threading.Lock()


def run_guarded(input_cls: type[TInput], kwargs: dict, fn: Callable[..., BaseModel]) -> dict:
    """Validate at boundary, serialize on the GPU lock, return output contract."""
    req = input_cls(**kwargs)
    try:
        with _INFERENCE_LOCK:
            return fn(req).model_dump()
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e
