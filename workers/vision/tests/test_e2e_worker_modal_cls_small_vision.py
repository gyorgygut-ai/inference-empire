import base64
import io

import pytest
from PIL import Image

import modal

from workers.vision._shared_small_vision import SmallVisionOutput
import workers.vision.worker_modal_cls_small_vision as worker_function

pytestmark = [
    pytest.mark.usefixtures("modal_worker_function_test"),
    pytest.mark.modal_worker_function_test(worker_function),
]


def _image_b64():
    img = Image.new("RGB", (8, 8), (0, 255, 0))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


GOOD = {"image_base64": _image_b64()}


def test_good_input_returns_contract():
    Cls = modal.Cls.from_name("small-vision-worker", "SmallVisionWorker")
    out = Cls().analyze.remote(**GOOD)
    assert SmallVisionOutput.model_validate(out).model_dump() == out