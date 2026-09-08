import base64
import io

import pytest
from PIL import Image

from workers.vision._shared_small_vision import SmallVisionOutput
import workers.vision.worker_flash_cls_small_vision as worker_function

pytestmark = pytest.mark.usefixtures("flash_worker_function_test")


def _image_b64():
    img = Image.new("RGB", (8, 8), (0, 255, 0))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


GOOD = {"image_base64": _image_b64()}


@pytest.mark.flash_worker_function_test(worker_function)
def test_invalid_input_rejects():
    with pytest.raises(RuntimeError, match="inference failed"):
        worker_function.Qwen2VLVisionWorker().analyze(**{})


@pytest.mark.flash_worker_function_test(worker_function)
def test_good_input_returns_contract():
    out = worker_function.Qwen2VLVisionWorker().analyze(**GOOD)
    assert SmallVisionOutput.model_validate(out).model_dump() == out