import base64
import io

import pytest
from PIL import Image
from shared.worker_vision import SmallVisionOutput

import apps.vision.worker_flash_cls_small_vision as worker_function  # ty: ignore[unresolved-import]

pytestmark = pytest.mark.skip(reason="flash dev not available")


def _image_b64():
    img = Image.new("RGB", (8, 8), (0, 255, 0))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def test_good_input_returns_contract():
    out = worker_function.Qwen2VLVisionWorker().generate(image_base64=_image_b64())
    assert SmallVisionOutput.model_validate(out).model_dump() == out
