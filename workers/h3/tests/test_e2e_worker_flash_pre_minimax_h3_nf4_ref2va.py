import pytest

import workers.h3.worker_flash_pre_minimax_h3_nf4_ref2va as worker_function
from workers.artifact_check import artifact_exists
from workers.h3._shared_minimax_h3_nf4_ref2va import Artifact, MiniMaxH3Nf4Ref2vaOutput

pytestmark = pytest.mark.skip(reason="flash dev not available")


def test_good_input_returns_contract_and_artifact():
    out = worker_function.MiniMaxH3Ref2vaWorker().generate(
        prompt="a cat walking in a garden", seed=7
    )
    url = out["artifact"]["presigned_url"]
    assert out == MiniMaxH3Nf4Ref2vaOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert artifact_exists(url, timeout=120)
