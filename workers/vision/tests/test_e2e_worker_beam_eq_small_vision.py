import base64
import io
import json
import os
from pathlib import Path

import httpx
import pytest
from PIL import Image

from workers.vision._shared_small_vision import SmallVisionOutput

CONTRACT = json.loads((Path(__file__).parent.parent / "contracts" / "small_vision.json").read_text())


def _image_b64():
    img = Image.new("RGB", (8, 8), (0, 255, 0))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


GOOD = {"image_base64": _image_b64()}


def _assert_contract(out: dict):
    # Validate required fields per contracts/small_vision.json (JSON-only, no artifact)
    assert "classification" in out, "output missing required field 'classification'"
    assert "subjects" in out, "output missing required field 'subjects'"
    assert "description" in out, "output missing required field 'description'"
    # Pydantic contract validation
    validated = SmallVisionOutput.model_validate(out)
    assert validated.classification
    assert isinstance(validated.subjects, list)
    assert validated.description
    # JSON schema required checks
    assert CONTRACT["output"]["required"] == ["classification", "subjects", "description"]


def _endpoint_url():
    url = os.environ.get("SMALL_VISION_BEAM_URL")
    assert url, "SMALL_VISION_BEAM_URL must point at the deployed small-vision-worker endpoint"
    return url


def test_invalid_input_rejects():
    r = httpx.post(_endpoint_url(), json={}, timeout=120)
    assert r.status_code != 200, "endpoint must reject input missing required 'image_base64'"


def test_good_input_returns_contract():
    r = httpx.post(_endpoint_url(), json=GOOD, timeout=300)
    assert r.status_code == 200, f"endpoint failed: {r.status_code} {r.text[:200]}"
    _assert_contract(r.json())
