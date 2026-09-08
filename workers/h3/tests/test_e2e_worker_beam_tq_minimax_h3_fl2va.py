import httpx
import pytest

from workers.h3._shared_minimax_h3_fl2va import Artifact, MiniMaxH3Fl2VAOutput
import workers.h3.worker_beam_tq_minimax_h3_fl2va as worker_function

pytestmark = [
    pytest.mark.usefixtures("beam_worker_function_test"),
    pytest.mark.beam_worker_function_test(worker_function),
]

GOOD = {"prompt": "a cat walking in a garden", "seed": 7}


def _artifact_exists(url: str) -> bool:
    try:
        response = httpx.get(url, timeout=120)
        return response.status_code == 200 and len(response.content) > 0
    except Exception:
        return False


def test_good_input_returns_contract_and_artifact():
    import workers.h3.worker_beam_tq_minimax_h3_fl2va as worker_mod

    task = worker_mod.dispatch.put(**GOOD)
    out = task.result(wait=True)
    assert out is not None, "beam task returned None - check beam logs"

    url = out["artifact"]["presigned_url"]
    assert out == MiniMaxH3Fl2VAOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert _artifact_exists(url)