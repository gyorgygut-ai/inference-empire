import subprocess

import modal
import pytest

import workers.flux2.worker_modal_cls_flux2_klein9b as worker_module
from workers.artifact_check import artifact_exists
from workers.flux2._shared_flux2_klein9b import Artifact, Flux2Klein9bOutput

APP_NAME = "flux2-klein9b-worker"
GOOD = {"prompt": "a red square", "seed": 7}


@pytest.fixture(scope="module")
def deployed_app():
    subprocess.run(["modal", "deploy", worker_module.__file__], check=True)
    yield
    subprocess.run(["modal", "app", "stop", APP_NAME, "--yes"], check=False)


def test_good_input_returns_contract_and_artifact(deployed_app):
    Cls = modal.Cls.from_name(APP_NAME, "FluxKleinWorker")
    call = Cls().generate.spawn(**GOOD)
    out = call.get(timeout=300)
    url = out["artifact"]["presigned_url"]
    assert out == Flux2Klein9bOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert artifact_exists(url)
