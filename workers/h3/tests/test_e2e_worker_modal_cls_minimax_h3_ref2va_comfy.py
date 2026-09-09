import subprocess

import modal

import workers.h3.worker_modal_cls_minimax_h3_ref2va_comfy as worker_module
from workers.artifact_check import artifact_exists
from workers.h3._shared_minimax_h3_ref2va_comfy import Artifact, MiniMaxH3Ref2VAComfyOutput


def test_good_input_returns_contract_and_artifact():
    subprocess.run(["modal", "deploy", worker_module.__file__], check=True)
    try:
        Cls = modal.Cls.from_name("minimax-h3-ref2va-comfy-worker", "MiniMaxH3Ref2VAComfyWorker")
        call = Cls().generate.spawn(prompt="a cat walking in a garden", seed=7)
        out = call.get(timeout=3600)
        url = out["artifact"]["presigned_url"]
        assert isinstance(out["video"], str) and len(out["video"]) > 0
        assert out == MiniMaxH3Ref2VAComfyOutput(
            artifact=Artifact(presigned_url=url), video=out["video"]
        ).model_dump()
        assert artifact_exists(url, timeout=120)
    finally:
        subprocess.run(["modal", "app", "stop", "minimax-h3-ref2va-comfy-worker", "--yes"], check=False)
