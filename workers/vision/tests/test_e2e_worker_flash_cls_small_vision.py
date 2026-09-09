import base64
import io

import pytest
from PIL import Image

import workers.vision.worker_flash_cls_small_vision as worker_function
from workers.vision._shared_small_vision import SmallVisionOutput

pytestmark = pytest.mark.skip(reason="flash dev not available")


def _image_b64():
    img = Image.new("RGB", (8, 8), (0, 255, 0))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def test_good_input_returns_contract():
    out = worker_function.Qwen2VLVisionWorker().analyze(image_base64=_image_b64())
    assert SmallVisionOutput.model_validate(out).model_dump() == out
