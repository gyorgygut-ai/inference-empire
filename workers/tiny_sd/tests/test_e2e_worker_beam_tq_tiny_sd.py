import httpx
import pytest

from workers.tiny_sd._shared_tiny_sd import Artifact, TinySDOutput
import workers.tiny_sd.worker_beam_tq_tiny_sd as worker_function

pytestmark = [
    pytest.mark.usefixtures("beam_worker_function_test"),
    pytest.mark.beam_worker_function_test(worker_function),
]

GOOD = {"prompt": "a red square", "seed": 7}


def _artifact_exists(url: str) -> bool:
    try:
        response = httpx.get(url, timeout=30)
        return response.status_code == 200 and len(response.content) > 0
    except Exception:
        return False


def test_invalid_input_rejects():
    import workers.tiny_sd.worker_beam_tq_tiny_sd as worker_mod

    task = worker_mod.dispatch.put(**{})
    with pytest.raises(RuntimeError, match="inference failed"):
        task.result(wait=True)


def test_good_input_returns_contract_and_artifact():
    import workers.tiny_sd.worker_beam_tq_tiny_sd as worker_mod

    task = worker_mod.dispatch.put(**GOOD)
    out = task.result(wait=True)
    assert out is not None, "beam task returned None - check beam logs"

    url = out["artifact"]["presigned_url"]
    assert out == TinySDOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert _artifact_exists(url)