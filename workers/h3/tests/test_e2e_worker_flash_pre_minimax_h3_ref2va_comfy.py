import pytest

import workers.h3.worker_flash_pre_minimax_h3_ref2va_comfy as worker_function
from workers.artifact_check import artifact_exists
from workers.h3._shared_minimax_h3_ref2va_comfy import Artifact, MiniMaxH3Ref2VAComfyOutput

pytestmark = pytest.mark.skip(reason="flash dev not available")


def test_good_input_returns_contract_and_artifact():
    out = worker_function.MiniMaxH3Ref2VAComfyWorker().generate(
        prompt="a cat walking in a garden", seed=7
    )
    url = out["artifact"]["presigned_url"]
    assert isinstance(out["video"], str) and len(out["video"]) > 0
    assert out == MiniMaxH3Ref2VAComfyOutput(
        artifact=Artifact(presigned_url=url), video=out["video"]
    ).model_dump()
    assert artifact_exists(url, timeout=120)
