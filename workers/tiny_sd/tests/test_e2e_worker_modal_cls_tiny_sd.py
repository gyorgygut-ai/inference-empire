import pytest

import httpx
import modal

from workers.tiny_sd._shared_tiny_sd import Artifact, TinySDOutput
import workers.tiny_sd.worker_modal_cls_tiny_sd as worker_function

pytestmark = pytest.mark.usefixtures("modal_worker_function_test")


def _artifact_exists(url: str) -> bool:
    try:
        response = httpx.get(url, timeout=30)
        return response.status_code == 200 and len(response.content) > 0
    except Exception:
        return False


@pytest.mark.modal_worker_function_test(worker_function)
def test_good_input_returns_contract_and_artifact():
    Cls = modal.Cls.from_name("tiny-sd-worker", "TinySDWorker")
    out = Cls().generate.remote(**{"prompt": "a red square", "seed": 7})
    url = out["artifact"]["presigned_url"]
    assert out == TinySDOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert _artifact_exists(url)
