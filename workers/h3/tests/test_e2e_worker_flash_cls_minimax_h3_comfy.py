import pytest

from workers.artifact_check import artifact_exists
from workers.h3._shared_minimax_h3_comfy import Artifact, MiniMaxH3ComfyOutput
import workers.h3.worker_flash_cls_minimax_h3_comfy as worker_function

pytestmark = pytest.mark.skip(reason="flash dev not available")

GOOD = {"prompt": "a cat walking in a garden", "seed": 7}


def test_good_input_returns_contract_and_artifact():
    out = worker_function.MiniMaxH3ComfyWorker().generate(**GOOD)
    url = out["artifact"]["presigned_url"]
    assert out == MiniMaxH3ComfyOutput(
        artifact=Artifact(presigned_url=url), video=out["video"]
    ).model_dump()
    assert artifact_exists(url, timeout=120)
