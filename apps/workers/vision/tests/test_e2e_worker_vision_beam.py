import base64
import io
import os

from PIL import Image
from shared.worker_vision import (
    SmallVisionInput,
    SmallVisionOutput,
    do_inference,
    load_dependencies,
)


def _image_b64():
    img = Image.new("RGB", (8, 8), (0, 255, 0))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def test_good_input_returns_contract():
    model, processor, analyze_prompt = load_dependencies()
    req = SmallVisionInput(image_base64=_image_b64())
    out = do_inference(model, processor, analyze_prompt, req)
    assert isinstance(out, SmallVisionOutput)
    assert out.classification
    assert out.subjects
    assert out.description


if __name__ == "__main__":
    os.environ.setdefault("HF_TOKEN", "")
    test_good_input_returns_contract()
    print("E2E PASSED")
