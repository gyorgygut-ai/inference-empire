import subprocess

import modal

import apps.h3.worker_modal_cls_minimax_h3_comfy as worker_module
from apps._artifact_check import artifact_exists
from apps.h3._shared_minimax_h3_comfy import Artifact, MiniMaxH3ComfyOutput


def test_good_input_returns_contract_and_artifact():
    subprocess.run(["modal", "deploy", worker_module.__file__], check=True)
    try:
        Cls = modal.Cls.from_name("minimax-h3-comfy-worker", "MiniMaxH3ComfyWorker")
        call = Cls().generate.spawn(prompt="a cat walking in a garden", seed=7)
        out = call.get(timeout=3600)
        url = out["artifact"]["presigned_url"]
        assert out == MiniMaxH3ComfyOutput(artifact=Artifact(presigned_url=url)).model_dump()
        assert artifact_exists(url)
    finally:
        subprocess.run(["modal", "app", "stop", "minimax-h3-comfy-worker", "--yes"], check=False)
