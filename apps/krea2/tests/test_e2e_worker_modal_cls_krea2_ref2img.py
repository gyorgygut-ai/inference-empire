import subprocess

import modal

import apps.krea2.worker_modal_cls_krea2_ref2img as worker_module
from apps._artifact_check import artifact_exists
from apps.krea2._shared_krea2_ref2img import Artifact, Krea2Ref2ImgOutput


def test_good_input_returns_contract_and_artifact():
    subprocess.run(["modal", "deploy", worker_module.__file__], check=True)
    try:
        Cls = modal.Cls.from_name("krea2-ref2img-worker", "Krea2Ref2ImgWorker")
        out = Cls().generate.remote(prompt="a red square", seed=7)
        url = out["artifact"]["presigned_url"]
        assert out == Krea2Ref2ImgOutput(artifact=Artifact(presigned_url=url)).model_dump()
        assert artifact_exists(url)
    finally:
        subprocess.run(["modal", "app", "stop", "krea2-ref2img-worker", "--yes"], check=False)
