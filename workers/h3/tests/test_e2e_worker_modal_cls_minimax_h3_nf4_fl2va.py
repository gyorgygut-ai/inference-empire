import subprocess

import modal

import workers.h3.worker_modal_cls_minimax_h3_nf4_fl2va as worker_module
from workers.artifact_check import artifact_exists
from workers.h3._shared_minimax_h3_nf4_fl2va import Artifact, MiniMaxH3Nf4Fl2vaOutput


def test_good_input_returns_contract_and_artifact():
    subprocess.run(["modal", "deploy", worker_module.__file__], check=True)
    try:
        Cls = modal.Cls.from_name("minimax-h3-nf4-fl2va-worker", "MiniMaxH3Fl2vaWorker")
        call = Cls().generate.spawn(prompt="a cat walking in a garden", seed=7)
        out = call.get(timeout=3600)
        url = out["artifact"]["presigned_url"]
        assert out == MiniMaxH3Nf4Fl2vaOutput(artifact=Artifact(presigned_url=url)).model_dump()
        assert artifact_exists(url, timeout=120)
    finally:
        subprocess.run(["modal", "app", "stop", "minimax-h3-nf4-fl2va-worker", "--yes"], check=False)
