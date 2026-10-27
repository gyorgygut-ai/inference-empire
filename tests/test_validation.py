from apps.workers.flux2.shared.validation import validate_image_b64
from apps.workers.krea2.shared.validation import validate_image_b64 as validate_krea
from apps.workers.vision.shared.validation import validate_image_b64 as validate_vision


def test_flux2_validation():
    assert validate_image_b64("data:image/png;base64,iVBORw0KGgo=", "image") is not None

def test_krea2_validation():
    assert validate_krea("data:image/png;base64,iVBORw0KGgo=", "image") is not None

def test_vision_validation():
    assert validate_vision("data:image/png;base64,iVBORw0KGgo=", "image") is not None
