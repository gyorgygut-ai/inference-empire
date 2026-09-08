import httpx
import pytest

from workers.krea2._shared_krea2_ref2img import Artifact, Krea2Ref2ImgOutput
import workers.krea2.worker_beam_tq_krea2_ref2img as worker_function

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


def test_good_input_returns_contract_and_artifact():
    import workers.krea2.worker_beam_tq_krea2_ref2img as worker_mod

    task = worker_mod.dispatch.put(**GOOD)
    out = task.result(wait=True)
    assert out is not None, "beam task returned None - check beam logs"

    url = out["artifact"]["presigned_url"]
    assert out == Krea2Ref2ImgOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert _artifact_exists(url)