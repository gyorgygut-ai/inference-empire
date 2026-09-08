import base64
import io

import pytest
from PIL import Image

from workers.vision._shared_small_vision import SmallVisionOutput
import workers.vision.worker_beam_tq_small_vision as worker_function

pytestmark = [
    pytest.mark.usefixtures("beam_worker_function_test"),
    pytest.mark.beam_worker_function_test(worker_function),
]


def _image_b64():
    img = Image.new("RGB", (8, 8), (0, 255, 0))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


GOOD = {"image_base64": _image_b64()}


def test_good_input_returns_contract():
    import workers.vision.worker_beam_tq_small_vision as worker_mod

    task = worker_mod.dispatch.put(**GOOD)
    out = task.result(wait=True)
    assert out is not None, "beam task returned None - check beam logs"

    assert SmallVisionOutput.model_validate(out).model_dump() == out