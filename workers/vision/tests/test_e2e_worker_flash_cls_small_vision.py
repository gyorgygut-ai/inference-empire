import base64
import io

import pytest
from PIL import Image

import workers.vision.worker_flash_cls_small_vision as worker_mod
from workers.services.inference.tiny_vision import TinyVisionModel, TinyVisionProcessor


def _image_b64():
    img = Image.new("RGB", (8, 8), (0, 255, 0))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


@pytest.mark.local_e2e
def test_e2e_flash_returns_result(e2e_target):
    deps = (TinyVisionModel(), TinyVisionProcessor(), "fake-prompt")

    out = e2e_target.run(worker_mod, {"image_base64": _image_b64()}, deps)

    assert "classification" in out
    assert "subjects" in out
    assert "description" in out
    assert isinstance(out["subjects"], list)


