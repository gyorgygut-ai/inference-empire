import pytest
from shared.worker_tiny_sd import Artifact, TinySDOutput

import apps.tiny_sd.worker_flash_cls_tiny_sd as worker_function  # ty: ignore[unresolved-import]

pytestmark = pytest.mark.skip(reason="flash dev not available")


def test_good_input_returns_contract_and_artifact(artifact_exists):
    out = worker_function.TinySDWorker().generate(prompt="a red square", seed=7)
    url = out["artifact"]["presigned_url"]
    assert out == TinySDOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert artifact_exists(url)
