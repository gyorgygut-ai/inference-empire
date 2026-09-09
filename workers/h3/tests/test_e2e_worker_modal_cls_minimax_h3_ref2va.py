import subprocess

import modal
import pytest

from workers.artifact_check import artifact_exists
from workers.h3._shared_minimax_h3_ref2va import Artifact, MiniMaxH3Ref2VAOutput

WORKER_FILE = "workers/h3/worker_modal_cls_minimax_h3_ref2va.py"
APP_NAME = "minimax-h3-ref2va-worker"
GOOD = {"prompt": "a cat walking in a garden", "seed": 7}


@pytest.fixture(scope="module")
def deployed_app():
    subprocess.run(["modal", "deploy", WORKER_FILE], check=True)
    yield
    subprocess.run(["modal", "app", "stop", APP_NAME, "--yes"], check=False)


def test_good_input_returns_contract_and_artifact(deployed_app):
    Cls = modal.Cls.from_name(APP_NAME, "MiniMaxH3Ref2VAWorker")
    call = Cls().generate.spawn(**GOOD)
    out = call.get(timeout=3600)
    url = out["artifact"]["presigned_url"]
    assert out == MiniMaxH3Ref2VAOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert artifact_exists(url, timeout=120)
