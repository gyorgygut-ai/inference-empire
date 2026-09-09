import base64
import io
import subprocess

import modal
from PIL import Image

import workers.vision.worker_modal_cls_small_vision as worker_module
from workers.vision._shared_small_vision import SmallVisionOutput


def _image_b64():
    img = Image.new("RGB", (8, 8), (0, 255, 0))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def test_good_input_returns_contract():
    subprocess.run(["modal", "deploy", worker_module.__file__], check=True)
    try:
        Cls = modal.Cls.from_name("small-vision-worker", "SmallVisionWorker")
        out = Cls().analyze.remote(image_base64=_image_b64())
        assert SmallVisionOutput.model_validate(out).model_dump() == out
    finally:
        subprocess.run(["modal", "app", "stop", "small-vision-worker", "--yes"], check=False)
