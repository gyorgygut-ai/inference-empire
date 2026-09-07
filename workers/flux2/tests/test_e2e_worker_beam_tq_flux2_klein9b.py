from types import SimpleNamespace

import httpx
import pytest

from workers.flux2._shared_flux2_klein9b import Artifact, Flux2Klein9bOutput
import workers.flux2.worker_beam_tq_flux2_klein9b as worker_function


@pytest.mark.beam_worker_function_test(worker_function)
def test_invalid_input_rejects():
    ctx = SimpleNamespace(on_start_value=worker_function.load_dependencies())
    with pytest.raises(Exception):
        worker_function.dispatch.local(ctx, {})


@pytest.mark.beam_worker_function_test(worker_function)
def test_good_input_returns_contract_and_artifact():
    ctx = SimpleNamespace(on_start_value=worker_function.load_dependencies())
    out = worker_function.dispatch.local(ctx, {"prompt": "a red square", "seed": 7})
    expected = Flux2Klein9bOutput(artifact=Artifact(presigned_url=out["artifact"]["presigned_url"])).model_dump()
    assert out == expected
    art = httpx.get(out["artifact"]["presigned_url"], timeout=30)
    assert art.status_code == 200 and len(art.content) > 0
