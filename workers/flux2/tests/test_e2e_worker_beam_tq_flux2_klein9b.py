import json
from pathlib import Path

import httpx
import pytest

from workers.flux2._shared_flux2_klein9b import Flux2Klein9bOutput

GOOD = {"prompt": "a red square", "seed": 7}
CONTRACT = json.loads((Path(__file__).parent.parent / "contracts" / "flux2_klein9b.json").read_text())


def _assert_contract(out: dict):
    assert "artifact" in out, "output missing required field 'artifact'"
    assert "presigned_url" in out["artifact"], "artifact missing required field 'presigned_url'"
    validated = Flux2Klein9bOutput.model_validate(out)
    assert validated.artifact.presigned_url.startswith("https://")
    assert CONTRACT["output"]["required"] == ["artifact"]
    assert CONTRACT["output"]["properties"]["artifact"]["required"] == ["presigned_url"]


def test_invalid_input_rejects(platform_beam):
    print("[beam] test_invalid_input_rejects: start", flush=True)
    task = platform_beam.put(**{})
    with pytest.raises(Exception):
        task.result(wait=True)


def test_good_input_returns_contract_and_artifact(platform_beam):
    print("[beam] test_good_input_returns_contract_and_artifact: start", flush=True)
    task = platform_beam.put(**GOOD)
    out = task.result(wait=True)

    _assert_contract(out)

    url = out["artifact"]["presigned_url"]
    art = httpx.get(url, timeout=30)
    assert art.status_code == 200
    assert len(art.content) > 0
    assert url.startswith("https://")
