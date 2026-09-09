import subprocess

import modal
import pytest

from workers.artifact_check import artifact_exists
from workers.tiny_sd._shared_tiny_sd import Artifact, TinySDOutput

WORKER_FILE = "workers/tiny_sd/worker_modal_cls_tiny_sd.py"
APP_NAME = "tiny-sd-worker"
GOOD = {"prompt": "a red square", "seed": 7}


@pytest.fixture(scope="module")
def deployed_app():
    subprocess.run(["modal", "deploy", WORKER_FILE], check=True)
    yield
    subprocess.run(["modal", "app", "stop", APP_NAME, "--yes"], check=False)


def test_good_input_returns_contract_and_artifact(deployed_app):
    Cls = modal.Cls.from_name(APP_NAME, "TinySDWorker")
    out = Cls().generate.remote(**GOOD)
    url = out["artifact"]["presigned_url"]
    assert out == TinySDOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert artifact_exists(url)
