import base64
import io

import pytest
from PIL import Image
from pydantic import ValidationError

import workers.vision.worker_flash_cls_small_vision as worker_mod
from workers.services.inference.vision_fake import FakeVisionModel, FakeVisionProcessor


def _image_b64():
    img = Image.new("RGB", (8, 8), (0, 255, 0))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


CANNED = {
    "classification": "landscape_0p",
    "subjects": ["green hill"],
    "description": "An 8x8 green square.",
}


def test_generate_returns_classification():
    out = worker_mod.generate(
        FakeVisionModel(CANNED),
        FakeVisionProcessor(CANNED),
        "fake-prompt",
        image_base64=_image_b64(),
    )

    assert out == CANNED


def test_generate_rejects_missing_image():
    with pytest.raises(ValidationError):
        worker_mod.generate(
            FakeVisionModel(CANNED), FakeVisionProcessor(CANNED), "fake-prompt"
        )
