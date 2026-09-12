"""Canonical base64 media validation for worker input boundaries.

Every worker that accepts base64 image/video/audio input must validate it
here, at the pydantic model boundary, BEFORE any model load or inference.
A bad input must raise ValueError (surfacing as ValidationError naming the
field) — never an UnidentifiedImageError/binascii traceback minutes later.

Canonical format: raw base64, no data-URL prefix. A data-URL prefix is
tolerated and stripped, but never required.
"""
from __future__ import annotations

import base64
import binascii
import io

MAX_IMAGE_B64_BYTES = 15 * 1024 * 1024  # decoded-bytes cap (decompression-bomb guard)
MAX_IMAGE_PIXELS = 64_000_000
MAX_MEDIA_B64_BYTES = 100 * 1024 * 1024  # video/audio decoded-bytes cap

_PATH_EXTS = (
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif",
    ".mp4", ".mov", ".mp3", ".wav", ".m4a", ".aac",
)


def strip_data_url(value: str) -> str:
    """Strip a data:...;base64, prefix, returning raw base64."""
    if value.startswith("data:") and "," in value:
        return value.split(",", 1)[1]
    return value


def looks_like_path(value: str) -> bool:
    """Heuristic: slashes, leading ~/., or a known media extension."""
    return (
        "/" in value
        or "\\" in value
        or value.startswith(("~", "."))
        or value.lower().endswith(_PATH_EXTS)
    )


def validate_media_b64(value: str, field: str) -> str:
    """Strict base64 + size cap for video/audio payloads. Returns raw b64."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: empty, expected base64 media data")
    raw = strip_data_url(value).strip()
    if looks_like_path(raw) and len(raw) < 1024:
        raise ValueError(
            f"{field}: looks like a file path {raw!r} — "
            "send file bytes as base64, not a path"
        )
    try:
        blob = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"{field}: not valid base64: {exc}") from exc
    if len(blob) > MAX_MEDIA_B64_BYTES:
        raise ValueError(
            f"{field}: decoded size {len(blob)} bytes exceeds "
            f"{MAX_MEDIA_B64_BYTES} byte cap"
        )
    if not blob:
        raise ValueError(f"{field}: decodes to empty bytes")
    return raw


def validate_image_b64(value: str, field: str) -> str:
    """Strict base64 + real-image check + pixel cap. Returns raw b64."""
    from PIL import Image

    raw = validate_media_b64(value, field)
    blob = base64.b64decode(raw, validate=True)
    if len(blob) > MAX_IMAGE_B64_BYTES:
        raise ValueError(
            f"{field}: decoded size {len(blob)} bytes exceeds "
            f"{MAX_IMAGE_B64_BYTES} byte cap"
        )
    try:
        with Image.open(io.BytesIO(blob)) as img:
            img.verify()
        with Image.open(io.BytesIO(blob)) as img:
            width, height = img.size
    except Exception as exc:
        preview = blob[:32]
        raise ValueError(
            f"{field}: decodes but is not an image "
            f"({len(blob)} bytes, starts with {preview!r}): {exc}"
        ) from exc
    pixels = width * height
    if pixels > MAX_IMAGE_PIXELS:
        raise ValueError(
            f"{field}: image {width}x{height} ({pixels} px) exceeds "
            f"{MAX_IMAGE_PIXELS} px cap"
        )
    if pixels == 0:
        raise ValueError(f"{field}: image has zero size")
    return raw
