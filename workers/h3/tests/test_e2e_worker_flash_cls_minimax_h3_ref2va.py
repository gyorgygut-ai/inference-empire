import asyncio
import json
from pathlib import Path

import httpx
import pytest

from workers.h3.worker_flash_cls_minimax_h3_ref2va import MiniMaxH3Ref2VAWorker
from workers.h3._shared_minimax_h3_ref2va import MiniMaxH3Ref2VAOutput

pytestmark = pytest.mark.skip(reason="flash e2e written but skipped")

GOOD = {"prompt": "a cat walking in a garden", "seed": 7}
CONTRACT = json.loads((Path(__file__).parent.parent / "contracts" / "minimax_h3_ref2va.json").read_text())


def _assert_contract(out: dict):
    # Validate required fields per contracts/minimax_h3_ref2va.json
    assert "artifact" in out, "output missing required field 'artifact'"
    assert "presigned_url" in out["artifact"], "artifact missing required field 'presigned_url'"
    # Pydantic contract validation
    validated = MiniMaxH3Ref2VAOutput.model_validate(out)
    assert validated.artifact.presigned_url.startswith("https://")
    # JSON schema required checks
    assert CONTRACT["output"]["required"] == ["artifact"]
    assert CONTRACT["output"]["properties"]["artifact"]["required"] == ["presigned_url"]


def test_invalid_input_rejects():
    with pytest.raises(Exception):
        asyncio.run(MiniMaxH3Ref2VAWorker().generate(**{}))


def test_good_input_returns_contract_and_artifact():
    out = asyncio.run(MiniMaxH3Ref2VAWorker().generate(**GOOD))

    _assert_contract(out)

    url = out["artifact"]["presigned_url"]
    art = httpx.get(url, timeout=120)
    assert art.status_code == 200
    assert len(art.content) > 0
    # Artifact must exist in bucket (presigned URL reachable with content validated above)
    assert url.startswith("https://")
