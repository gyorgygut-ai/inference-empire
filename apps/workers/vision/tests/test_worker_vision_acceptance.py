"""Acceptance test for worker-vision.

Runs after deploy-beam; proves the deployed worker serves a request.
"""
import base64
import io
import os
import urllib.request

import pytest
from PIL import Image


def test_worker_vision_acceptance():
    """Ping the deployed worker-vision and assert it returns a valid contract."""
    img = Image.new("RGB", (8, 8), (0, 255, 0))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    image_b64 = base64.b64encode(buffer.getvalue()).decode()
    payload = (
        '{"image_base64":"' + image_b64 + '","prompt":"describe this","negative_prompt":""}'
    ).encode()
    url = os.environ["SECRET_WORKER_VISION_URL"]
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        assert resp.status == 200
        body = resp.read().decode()
    assert "classification" in body
    assert "subjects" in body
    assert "description" in body