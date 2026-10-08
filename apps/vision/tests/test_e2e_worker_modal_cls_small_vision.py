import base64
import io

import modal
from PIL import Image

from packages.vision.shared import SmallVisionOutput


def _image_b64():
    img = Image.new("RGB", (8, 8), (0, 255, 0))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def test_good_input_returns_contract():
    Cls = modal.Cls.from_name("small-vision-worker", "SmallVisionWorker")
    out = Cls().generate.remote(image_base64=_image_b64())
    assert SmallVisionOutput.model_validate(out).model_dump() == out
