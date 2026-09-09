import subprocess

import modal
import pytest

import workers.h3.worker_modal_cls_minimax_h3_comfy as worker_module
from workers.artifact_check import artifact_exists
from workers.h3._shared_minimax_h3_comfy import Artifact, MiniMaxH3ComfyOutput

APP_NAME = "minimax-h3-comfy-worker"
GOOD = {"prompt": "a cat walking in a garden", "seed": 7}


@pytest.fixture(scope="module")
def deployed_app():
    subprocess.run(["modal", "deploy", worker_module.__file__], check=True)
    yield
    subprocess.run(["modal", "app", "stop", APP_NAME, "--yes"], check=False)


def test_good_input_returns_contract_and_artifact(deployed_app):
    Cls = modal.Cls.from_name(APP_NAME, "MiniMaxH3ComfyWorker")
    call = Cls().generate.spawn(**GOOD)
    out = call.get(timeout=3600)
    url = out["artifact"]["presigned_url"]
    assert isinstance(out["video"], str) and len(out["video"]) > 0
    assert out == MiniMaxH3ComfyOutput(
        artifact=Artifact(presigned_url=url), video=out["video"]
    ).model_dump()
    assert artifact_exists(url, timeout=120)
