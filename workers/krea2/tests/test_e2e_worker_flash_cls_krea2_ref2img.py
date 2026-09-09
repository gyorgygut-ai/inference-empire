import pytest

import workers.krea2.worker_flash_cls_krea2_ref2img as worker_function
from workers.artifact_check import artifact_exists
from workers.krea2._shared_krea2_ref2img import Artifact, Krea2Ref2ImgOutput

pytestmark = pytest.mark.skip(reason="flash dev not available")


def test_good_input_returns_contract_and_artifact():
    out = worker_function.Krea2Ref2ImgWorker().generate(prompt="a red square", seed=7)
    url = out["artifact"]["presigned_url"]
    assert out == Krea2Ref2ImgOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert artifact_exists(url)
