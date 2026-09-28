import base64
import io

import pytest

from packages.media.validation import (
    validate_image_b64,
    validate_media_b64,
)

# 1x1 red PNG, raw base64 (no data-URL prefix).
TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _png_b64(width: int, height: int) -> str:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (width, height), (255, 0, 0)).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def test_path_string_rejected_with_field_and_hint():
    with pytest.raises(ValueError, match=r"first_frame.*file path.*base64, not a path"):
        validate_image_b64("../faces22/ys.png", "first_frame")


def test_garbage_base64_rejected():
    with pytest.raises(ValueError, match=r"first_frame.*not valid base64"):
        validate_image_b64("!!!not-base64!!!", "first_frame")


def test_valid_base64_non_image_rejected_with_preview():
    blob = base64.b64encode(b"../faces22/ys.png padding to pass path check x" * 4).decode()
    with pytest.raises(ValueError, match=r"first_frame.*not an image"):
        validate_image_b64(blob, "first_frame")


def test_empty_rejected():
    with pytest.raises(ValueError, match="empty"):
        validate_image_b64("   ", "first_frame")


def test_data_url_prefix_tolerated_and_stripped():
    out = validate_image_b64(f"data:image/png;base64,{TINY_PNG_B64}", "first_frame")
    assert out == TINY_PNG_B64
    assert not out.startswith("data:")


def test_happy_path_returns_raw_b64():
    assert validate_image_b64(TINY_PNG_B64, "first_frame") == TINY_PNG_B64


def test_pixel_cap_enforced(monkeypatch):
    import packages.media.validation as v

    monkeypatch.setattr(v, "MAX_IMAGE_PIXELS", 1)
    with pytest.raises(ValueError, match=r"exceeds .* px cap"):
        validate_image_b64(_png_b64(4, 4), "first_frame")


def test_media_b64_accepts_non_image_bytes():
    blob = base64.b64encode(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 100).decode()
    assert validate_media_b64(blob, "ref_videos[0]") == blob


def test_media_b64_rejects_path():
    with pytest.raises(ValueError, match=r"ref_audios\[0\].*file path"):
        validate_media_b64("./clip.mp3", "ref_audios[0]")


def test_media_byte_cap_enforced(monkeypatch):
    import packages.media.validation as v

    monkeypatch.setattr(v, "MAX_MEDIA_B64_BYTES", 10)
    blob = base64.b64encode(b"x" * 64).decode()
    with pytest.raises(ValueError, match=r"exceeds .* byte cap"):
        validate_media_b64(blob, "ref_videos[0]")
