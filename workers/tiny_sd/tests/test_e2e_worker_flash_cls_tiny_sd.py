import pytest

import workers.tiny_sd.worker_flash_cls_tiny_sd as worker_function
from workers.artifact_check import artifact_exists
from workers.tiny_sd._shared_tiny_sd import Artifact, TinySDOutput

pytestmark = pytest.mark.skip(reason="flash dev not available")


def test_good_input_returns_contract_and_artifact():
    out = worker_function.TinySDWorker().generate(prompt="a red square", seed=7)
    url = out["artifact"]["presigned_url"]
    assert out == TinySDOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert artifact_exists(url)
