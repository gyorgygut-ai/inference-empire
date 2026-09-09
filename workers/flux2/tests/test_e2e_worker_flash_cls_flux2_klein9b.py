import pytest

from workers.artifact_check import artifact_exists
from workers.flux2._shared_flux2_klein9b import Artifact, Flux2Klein9bOutput
import workers.flux2.worker_flash_cls_flux2_klein9b as worker_function

pytestmark = pytest.mark.skip(reason="flash dev not available")

GOOD = {"prompt": "a red square", "seed": 7}


def test_good_input_returns_contract_and_artifact():
    out = worker_function.FluxKleinWorker().generate(**GOOD)
    url = out["artifact"]["presigned_url"]
    assert out == Flux2Klein9bOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert artifact_exists(url)
