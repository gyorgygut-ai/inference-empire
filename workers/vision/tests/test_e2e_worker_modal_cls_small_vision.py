import base64
import io
import subprocess

import modal
import pytest
from PIL import Image

import workers.vision.worker_modal_cls_small_vision as worker_module
from workers.vision._shared_small_vision import SmallVisionOutput

APP_NAME = "small-vision-worker"


def _image_b64():
    img = Image.new("RGB", (8, 8), (0, 255, 0))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


GOOD = {"image_base64": _image_b64()}


@pytest.fixture(scope="module")
def deployed_app():
    subprocess.run(["modal", "deploy", worker_module.__file__], check=True)
    yield
    subprocess.run(["modal", "app", "stop", APP_NAME, "--yes"], check=False)


def test_good_input_returns_contract(deployed_app):
    Cls = modal.Cls.from_name(APP_NAME, "SmallVisionWorker")
    out = Cls().analyze.remote(**GOOD)
    assert SmallVisionOutput.model_validate(out).model_dump() == out
