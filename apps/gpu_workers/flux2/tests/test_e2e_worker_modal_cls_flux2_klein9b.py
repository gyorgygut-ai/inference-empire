import subprocess

import modal

import apps.gpu_workers.flux2.worker_modal_cls_flux2_klein9b as worker_module
from apps.gpu_workers.artifact_check import artifact_exists
from apps.gpu_workers.flux2._shared_flux2_klein9b import Artifact, Flux2Klein9bOutput


def test_good_input_returns_contract_and_artifact():
    subprocess.run(["modal", "deploy", worker_module.__file__], check=True)
    try:
        Cls = modal.Cls.from_name("flux2-klein9b-worker", "FluxKleinWorker")
        call = Cls().generate.spawn(prompt="a red square", seed=7)
        out = call.get(timeout=600)
        url = out["artifact"]["presigned_url"]
        assert out == Flux2Klein9bOutput(artifact=Artifact(presigned_url=url)).model_dump()
        assert artifact_exists(url)
    finally:
        subprocess.run(["modal", "app", "stop", "flux2-klein9b-worker", "--yes"], check=False)
