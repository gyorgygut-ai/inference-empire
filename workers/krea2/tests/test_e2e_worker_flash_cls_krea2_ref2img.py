import httpx
import pytest

from workers.krea2._shared_krea2_ref2img import Artifact, Krea2Ref2ImgOutput
import workers.krea2.worker_flash_cls_krea2_ref2img as worker_function


def _artifact_exists(url: str) -> bool:
    try:
        response = httpx.get(url, timeout=30)
        return response.status_code == 200 and len(response.content) > 0
    except Exception:
        return False


@pytest.mark.flash_worker_function_test(worker_function)
def test_invalid_input_rejects():
    with pytest.raises(RuntimeError, match="inference failed"):
        worker_function.Krea2Ref2ImgWorker().generate(**{})


@pytest.mark.flash_worker_function_test(worker_function)
def test_good_input_returns_contract_and_artifact():
    out = worker_function.Krea2Ref2ImgWorker().generate(**{"prompt": "a red square", "seed": 7})
    url = out["artifact"]["presigned_url"]
    assert out == Krea2Ref2ImgOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert _artifact_exists(url)