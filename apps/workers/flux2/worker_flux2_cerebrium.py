from __future__ import annotations

from dist.contract_flux2 import Artifact, Input as Flux2Klein9bInput, Output as Flux2Klein9bOutput
from shared.worker_flux2 import do_inference, load_dependencies

__all__ = ["Artifact", "Flux2Klein9bInput", "Flux2Klein9bOutput", "run"]

storage, pipe, torch_module = load_dependencies()

def run(input_dict: dict) -> dict:
    req = Flux2Klein9bInput(**input_dict)
    result = do_inference(pipe, torch_module, storage, req)
    return result.model_dump()
