import httpx
import pytest

from workers.h3._shared_minimax_h3_ref2va import Artifact, MiniMaxH3Ref2VAOutput
import workers.h3.worker_modal_cls_minimax_h3_ref2va as worker_function


def _artifact_exists(url: str) -> bool:
    try:
        response = httpx.get(url, timeout=120)
        return response.status_code == 200 and len(response.content) > 0
    except Exception:
        return False


@pytest.mark.modal_worker_function_test(worker_function)
def test_invalid_input_rejects():
    with pytest.raises(RuntimeError, match="inference failed"):
        worker_function.MiniMaxH3Ref2VAWorker().generate(**{})


@pytest.mark.modal_worker_function_test(worker_function)
def test_good_input_returns_contract_and_artifact():
    out = worker_function.MiniMaxH3Ref2VAWorker().generate(
        **{"prompt": "a cat walking in a garden", "seed": 7}
    )
    url = out["artifact"]["presigned_url"]
    assert out == MiniMaxH3Ref2VAOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert _artifact_exists(url)