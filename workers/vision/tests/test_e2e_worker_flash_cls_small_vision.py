import asyncio
import base64
import io
import json
from pathlib import Path

import pytest
from PIL import Image

from workers.vision._shared_small_vision import SmallVisionOutput
from workers.vision.worker_flash_cls_small_vision import Qwen2VLVisionWorker

pytestmark = pytest.mark.skip(reason="flash e2e written but skipped")

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


def test_invalid_input_rejects():
    with pytest.raises(Exception):
        asyncio.run(Qwen2VLVisionWorker().analyze(**{}))


@pytest.mark.skip(reason="flash dev not available")
def test_good_input_returns_contract():
    out = asyncio.run(Qwen2VLVisionWorker().analyze(**GOOD))

    _assert_contract(out)
