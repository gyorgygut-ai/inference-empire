from types import SimpleNamespace

import httpx
import pytest

from workers.flux2._shared_flux2_klein9b import Artifact, Flux2Klein9bOutput
import workers.flux2.worker_beam_tq_flux2_klein9b as worker_function


def _artifact_exists(url: str) -> bool:
    try:
        response = httpx.get(url, timeout=30)
        return response.status_code == 200 and len(response.content) > 0
    except Exception:
        return False


@pytest.mark.beam_worker_function_test(worker_function)
def test_invalid_input_rejects():
    ctx = SimpleNamespace(on_start_value=worker_function.load_dependencies())
    with pytest.raises(RuntimeError, match="inference failed"):
        worker_function.dispatch.local(ctx, {})


@pytest.mark.beam_worker_function_test(worker_function)
def test_good_input_returns_contract_and_artifact():
    ctx = SimpleNamespace(on_start_value=worker_function.load_dependencies())
    out = worker_function.dispatch.local(ctx, {"prompt": "a red square", "seed": 7})
    url = out["artifact"]["presigned_url"]
    assert out == Flux2Klein9bOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert _artifact_exists(url)
