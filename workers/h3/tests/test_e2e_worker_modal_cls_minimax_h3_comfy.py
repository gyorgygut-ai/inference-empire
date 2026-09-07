import json
from pathlib import Path

import httpx
import modal
import pytest

from workers.h3._shared_minimax_h3_comfy import MiniMaxH3ComfyOutput

CONTRACT = json.loads((Path(__file__).parent.parent / "contracts" / "minimax_h3_comfy.json").read_text())

GOOD = {"prompt": "a cat walking in a garden", "seed": 7}


def _assert_contract(out: dict):
    # Validate required fields per contracts/minimax_h3_comfy.json
    assert "artifact" in out, "output missing required field 'artifact'"
    assert "video" in out, "output missing required field 'video'"
    # Pydantic contract validation
    validated = MiniMaxH3ComfyOutput.model_validate(out)
    assert validated.artifact.presigned_url.startswith("https://")
    assert validated.video
    # JSON schema required checks
    assert CONTRACT["output"]["required"] == ["artifact", "video"]
    assert CONTRACT["output"]["properties"]["artifact"]["required"] == ["presigned_url"]


def test_invalid_input_rejects():
    handle = modal.Cls.from_name("minimax-h3-comfy-worker", "MiniMaxH3ComfyWorker")().generate
    with pytest.raises(Exception):
        handle.spawn(**{}).get()


def test_good_input_returns_contract_and_artifact():
    handle = modal.Cls.from_name("minimax-h3-comfy-worker", "MiniMaxH3ComfyWorker")().generate
    out = handle.spawn(**GOOD).get()

    _assert_contract(out)

    # Artifact must exist in bucket
    r = httpx.get(out["artifact"]["presigned_url"], timeout=120)
    assert r.status_code == 200
    assert len(r.content) > 0
