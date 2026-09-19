import subprocess

import modal

import apps.gpu_workers.tiny_sd.worker_modal_cls_tiny_sd as worker_module
from apps.gpu_workers.artifact_check import artifact_exists
from apps.gpu_workers.tiny_sd._shared_tiny_sd import Artifact, TinySDOutput


def test_good_input_returns_contract_and_artifact():
    subprocess.run(["modal", "deploy", worker_module.__file__], check=True)
    try:
        Cls = modal.Cls.from_name("tiny-sd-worker", "TinySDWorker")
        out = Cls().generate.remote(prompt="a red square", seed=7)
        url = out["artifact"]["presigned_url"]
        assert out == TinySDOutput(artifact=Artifact(presigned_url=url)).model_dump()
        assert artifact_exists(url)
    finally:
        subprocess.run(["modal", "app", "stop", "tiny-sd-worker", "--yes"], check=False)
