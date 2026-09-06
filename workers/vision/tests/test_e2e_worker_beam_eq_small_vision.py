import base64
import io

import pytest
from PIL import Image

import workers.vision.worker_beam_eq_small_vision as worker_mod
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


@pytest.mark.local_e2e
def test_e2e_beam_returns_canned_result(e2e_target, bucket):
    deps = (FakeVisionModel(CANNED), FakeVisionProcessor(CANNED), "fake-prompt")

    out = e2e_target.run(worker_mod, {"image_base64": _image_b64()}, deps, bucket)

    assert out == CANNED


@pytest.mark.deployed_e2e
def test_e2e_beam_returns_canned_result_deployed(e2e_target, bucket):
    deps = (FakeVisionModel(CANNED), FakeVisionProcessor(CANNED), "fake-prompt")

    out = e2e_target.run(worker_mod, {"image_base64": _image_b64()}, deps, bucket)

    assert out == CANNED
