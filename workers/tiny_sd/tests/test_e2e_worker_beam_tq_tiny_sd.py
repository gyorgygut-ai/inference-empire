from types import SimpleNamespace

import pytest

import httpx

from workers.tiny_sd._shared_tiny_sd import Artifact, TinySDOutput
import workers.tiny_sd.worker_beam_tq_tiny_sd as worker_function


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
    assert out == TinySDOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert _artifact_exists(url)
