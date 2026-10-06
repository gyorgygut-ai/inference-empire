import pytest

import apps.flux2.worker_flash_cls_flux2_klein9b as worker_function
from apps.flux2._shared_flux2_klein9b import Artifact, Flux2Klein9bOutput

pytestmark = pytest.mark.skip(reason="flash dev not available")


def test_good_input_returns_contract_and_artifact(artifact_exists):
    out = worker_function.FluxKleinWorker().generate(prompt="a red square", seed=7)
    url = out["artifact"]["presigned_url"]
    assert out == Flux2Klein9bOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert artifact_exists(url)
