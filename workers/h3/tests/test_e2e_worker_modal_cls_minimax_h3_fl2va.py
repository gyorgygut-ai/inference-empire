import json
from pathlib import Path

import httpx
import modal
import pytest

from workers.h3._shared_minimax_h3_fl2va import MiniMaxH3Fl2VAOutput

CONTRACT = json.loads((Path(__file__).parent.parent / "contracts" / "minimax_h3_fl2va.json").read_text())

GOOD = {"prompt": "a cat walking in a garden", "seed": 7}


def _assert_contract(out: dict):
    # Validate required fields per contracts/minimax_h3_fl2va.json
    assert "artifact" in out, "output missing required field 'artifact'"
    # Pydantic contract validation
    validated = MiniMaxH3Fl2VAOutput.model_validate(out)
    assert validated.artifact.presigned_url.startswith("https://")
    # JSON schema required checks
    assert CONTRACT["output"]["required"] == ["artifact"]
    assert CONTRACT["output"]["properties"]["artifact"]["required"] == ["presigned_url"]


def test_invalid_input_rejects():
    handle = modal.Cls.from_name("minimax-h3-fl2va-worker", "MiniMaxH3Fl2VAWorker")().generate
    with pytest.raises(Exception):
        handle.spawn(**{}).get()


def test_good_input_returns_contract_and_artifact():
    handle = modal.Cls.from_name("minimax-h3-fl2va-worker", "MiniMaxH3Fl2VAWorker")().generate
    out = handle.spawn(**GOOD).get()

    _assert_contract(out)

    # Artifact must exist in bucket
    r = httpx.get(out["artifact"]["presigned_url"], timeout=120)
    assert r.status_code == 200
    assert len(r.content) > 0
