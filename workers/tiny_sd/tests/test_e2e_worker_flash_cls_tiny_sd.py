import asyncio
import json
from pathlib import Path

import httpx
import pytest

from workers.tiny_sd._shared_tiny_sd import TinySDOutput
from workers.tiny_sd.worker_flash_cls_tiny_sd import TinySDWorker

GOOD = {"prompt": "a red square", "seed": 7}
CONTRACT = json.loads((Path(__file__).parent.parent / "contracts" / "tiny_sd.json").read_text())


def _assert_contract(out: dict):
    # Validate required fields per contracts/tiny_sd.json
    assert "artifact" in out, "output missing required field 'artifact'"
    assert "presigned_url" in out["artifact"], "artifact missing required field 'presigned_url'"
    # Pydantic contract validation
    validated = TinySDOutput.model_validate(out)
    assert validated.artifact.presigned_url.startswith("https://")
    # JSON schema required checks
    assert CONTRACT["output"]["required"] == ["artifact"]
    assert CONTRACT["output"]["properties"]["artifact"]["required"] == ["presigned_url"]


def test_invalid_input_rejects():
    with pytest.raises(Exception):
        asyncio.run(TinySDWorker().generate(**{}))


@pytest.mark.skip(reason="flash dev not available")
def test_good_input_returns_contract_and_artifact():
    out = asyncio.run(TinySDWorker().generate(**GOOD))

    _assert_contract(out)

    url = out["artifact"]["presigned_url"]
    art = httpx.get(url, timeout=30)
    assert art.status_code == 200
    assert len(art.content) > 0
    # Artifact must exist in bucket (presigned URL reachable with content validated above)
    assert url.startswith("https://")
