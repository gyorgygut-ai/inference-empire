import subprocess

import modal
import pytest

from workers.artifact_check import artifact_exists
from workers.krea2._shared_krea2_ref2img import Artifact, Krea2Ref2ImgOutput

WORKER_FILE = "workers/krea2/worker_modal_cls_krea2_ref2img.py"
APP_NAME = "krea2-ref2img-worker"
GOOD = {"prompt": "a red square", "seed": 7}


@pytest.fixture(scope="module")
def deployed_app():
    subprocess.run(["modal", "deploy", WORKER_FILE], check=True)
    yield
    subprocess.run(["modal", "app", "stop", APP_NAME, "--yes"], check=False)


def test_good_input_returns_contract_and_artifact(deployed_app):
    Cls = modal.Cls.from_name(APP_NAME, "Krea2Ref2ImgWorker")
    out = Cls().generate.remote(**GOOD)
    url = out["artifact"]["presigned_url"]
    assert out == Krea2Ref2ImgOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert artifact_exists(url)
