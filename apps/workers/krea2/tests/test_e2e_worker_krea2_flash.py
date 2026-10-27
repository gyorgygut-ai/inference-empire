import pytest

import apps.workers.krea2.worker_krea2_flash as worker_function
from apps.workers.krea2.shared.worker_krea2 import Artifact, Krea2Ref2ImgOutput

pytestmark = pytest.mark.skip(reason="flash dev not available")


def test_good_input_returns_contract_and_artifact(artifact_exists):
    out = worker_function.Krea2Ref2ImgWorker().generate(prompt="a red square", seed=7)
    url = out["artifact"]["presigned_url"]
    assert out == Krea2Ref2ImgOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert artifact_exists(url)
