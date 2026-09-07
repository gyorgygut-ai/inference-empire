import json
from pathlib import Path

import httpx
import modal
import pytest

from workers.tiny_sd._shared_tiny_sd import TinySDOutput

GOOD = {"prompt": "a red square", "seed": 7}
CONTRACT = json.loads((Path(__file__).parent.parent / "contracts" / "tiny_sd.json").read_text())


def _assert_contract(out: dict):
    assert "artifact" in out, "output missing required field 'artifact'"
    assert "presigned_url" in out["artifact"], "artifact missing required field 'presigned_url'"
    validated = TinySDOutput.model_validate(out)
    assert validated.artifact.presigned_url.startswith("https://")
    assert CONTRACT["output"]["required"] == ["artifact"]
    assert CONTRACT["output"]["properties"]["artifact"]["required"] == ["presigned_url"]


def test_invalid_input_rejects(platform_modal):
    handle = modal.Cls.from_name("tiny-sd-worker", "TinySDWorker")().generate
    with pytest.raises(Exception):
        handle.spawn(**{}).get()


def test_good_input_returns_contract_and_artifact(platform_modal):
    handle = modal.Cls.from_name("tiny-sd-worker", "TinySDWorker")().generate
    out = handle.spawn(**GOOD).get()

    _assert_contract(out)

    url = out["artifact"]["presigned_url"]
    art = httpx.get(url, timeout=30)
    assert art.status_code == 200
    assert len(art.content) > 0
    assert url.startswith("https://")
