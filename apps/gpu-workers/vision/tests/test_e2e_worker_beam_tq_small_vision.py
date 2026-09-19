import base64
import io

from PIL import Image

from apps.gpu_workers.vision._shared_small_vision import SmallVisionOutput


def _image_b64():
    img = Image.new("RGB", (8, 8), (0, 255, 0))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def test_good_input_returns_contract():
    import apps.gpu_workers.vision.worker_beam_tq_small_vision as worker_mod

    task = worker_mod.dispatch.put(image_base64=_image_b64())
    out = task.result(wait=True)
    assert out is not None, "beam task returned None - check beam logs"

    assert SmallVisionOutput.model_validate(out).model_dump() == out
