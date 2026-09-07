import json
from pathlib import Path

import httpx
import pytest

from workers.krea2._shared_krea2_ref2img import Krea2Ref2ImgOutput

GOOD = {"prompt": "a red square", "seed": 7}
CONTRACT = json.loads((Path(__file__).parent.parent / "contracts" / "krea2_ref2img.json").read_text())


def _assert_contract(out: dict):
    assert "artifact" in out, "output missing required field 'artifact'"
    assert "presigned_url" in out["artifact"], "artifact missing required field 'presigned_url'"
    validated = Krea2Ref2ImgOutput.model_validate(out)
    assert validated.artifact.presigned_url.startswith("https://")
    assert CONTRACT["output"]["required"] == ["artifact"]
    assert CONTRACT["output"]["properties"]["artifact"]["required"] == ["presigned_url"]


def test_invalid_input_rejects():
    import workers.krea2.worker_beam_tq_krea2_ref2img as worker_mod

    task = worker_mod.dispatch.put(**{})
    with pytest.raises(Exception):
        task.result(wait=True)


def test_good_input_returns_contract_and_artifact():
    import workers.krea2.worker_beam_tq_krea2_ref2img as worker_mod

    task = worker_mod.dispatch.put(**GOOD)
    out = task.result(wait=True)
    assert out is not None, "beam task returned None - check beam logs"

    _assert_contract(out)

    url = out["artifact"]["presigned_url"]
    art = httpx.get(url, timeout=30)
    assert art.status_code == 200
    assert len(art.content) > 0
    assert url.startswith("https://")
