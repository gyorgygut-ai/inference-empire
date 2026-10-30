from __future__ import annotations

from dist.contract_krea2 import Artifact, Input as Krea2Ref2ImgInput, Output as Krea2Ref2ImgOutput
from shared.worker_krea2 import do_inference, load_dependencies

__all__ = ["Artifact", "Krea2Ref2ImgInput", "Krea2Ref2ImgOutput", "run"]

storage, pipe, runtime_dir, torch_module = load_dependencies(cache_dir=None)

def run(input_dict: dict) -> dict:
    req = Krea2Ref2ImgInput(**input_dict)
    result = do_inference(pipe, runtime_dir, torch_module, storage, req)
    return result.model_dump()
