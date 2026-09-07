import asyncio
import json
from pathlib import Path

import httpx
import pytest

from workers.krea2._shared_krea2_ref2img import Krea2Ref2ImgOutput
from workers.krea2.worker_flash_cls_krea2_ref2img import Krea2Ref2ImgWorker

GOOD = {"prompt": "a red square", "seed": 7}
CONTRACT = json.loads((Path(__file__).parent.parent / "contracts" / "krea2_ref2img.json").read_text())


def _assert_contract(out: dict):
    # Validate required fields per contracts/krea2_ref2img.json
    assert "artifact" in out, "output missing required field 'artifact'"
    assert "presigned_url" in out["artifact"], "artifact missing required field 'presigned_url'"
    # Pydantic contract validation
    validated = Krea2Ref2ImgOutput.model_validate(out)
    assert validated.artifact.presigned_url.startswith("https://")
    # JSON schema required checks
    assert CONTRACT["output"]["required"] == ["artifact"]
    assert CONTRACT["output"]["properties"]["artifact"]["required"] == ["presigned_url"]


def test_invalid_input_rejects():
    with pytest.raises(Exception):
        asyncio.run(Krea2Ref2ImgWorker().generate(**{}))


@pytest.mark.skip(reason="flash dev not available")
def test_good_input_returns_contract_and_artifact():
    out = asyncio.run(Krea2Ref2ImgWorker().generate(**GOOD))

    _assert_contract(out)

    url = out["artifact"]["presigned_url"]
    art = httpx.get(url, timeout=30)
    assert art.status_code == 200
    assert len(art.content) > 0
    # Artifact must exist in bucket (presigned URL reachable with content validated above)
    assert url.startswith("https://")
