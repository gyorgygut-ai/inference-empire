from __future__ import annotations

import logging
import os
import threading

from dist.contract_flux2 import Input as Flux2Klein9bInput
from dist.contract_flux2 import Output as Flux2Klein9bOutput
from fastapi import FastAPI, HTTPException
from shared.worker_flux2 import do_inference, load_dependencies, load_pipeline_lazy

MODEL_CACHE_DIR = os.environ.get("FLUX2_MODEL_CACHE_DIR", "/mnt/flux2-cache")
_runtime_lock = threading.Lock()
_storage = None
_pipe = None
_torch_module = None

app = FastAPI(title="worker-flux2")
logger = logging.getLogger(__name__)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/generate", response_model=Flux2Klein9bOutput)
def generate(request: Flux2Klein9bInput) -> Flux2Klein9bOutput:
    global _pipe, _storage, _torch_module

    try:
        with _runtime_lock:
            if _storage is None:
                _storage, _, _torch_module = load_dependencies()
            if _pipe is None:
                _pipe, _torch_module = load_pipeline_lazy(cache_dir=MODEL_CACHE_DIR)
            return do_inference(_pipe, _torch_module, _storage, request)
    except Exception as error:
        logger.exception("Azure Flux 2 generation failed")
        raise HTTPException(status_code=500, detail="Flux 2 generation failed") from error
