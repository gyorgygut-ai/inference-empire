import httpx
import pytest

from workers.flux2._shared_flux2_klein9b import Artifact, Flux2Klein9bOutput
import workers.flux2.worker_flash_cls_flux2_klein9b as worker_function


@pytest.mark.flash_worker_function_test(worker_function)
def test_invalid_input_rejects():
    with pytest.raises(Exception):
        worker_function.FluxKleinWorker().generate(**{})


@pytest.mark.flash_worker_function_test(worker_function)
def test_good_input_returns_contract_and_artifact():
    out = worker_function.FluxKleinWorker().generate(**{"prompt": "a red square", "seed": 7})
    expected = Flux2Klein9bOutput(artifact=Artifact(presigned_url=out["artifact"]["presigned_url"])).model_dump()
    assert out == expected
    art = httpx.get(out["artifact"]["presigned_url"], timeout=30)
    assert art.status_code == 200 and len(art.content) > 0
