"""Acceptance test for worker-tiny_sd.

Runs after deploy-beam; proves the deployed worker serves a request.
"""
import os
import urllib.request

import pytest


def test_worker_tiny_sd_acceptance():
    """Ping the deployed worker-tiny_sd and assert it returns a valid contract."""
    url = os.environ["SECRET_WORKER_TINY_SD_URL"]
    payload = b'{"prompt":"a tiny square","negative_prompt":"","width":512,"height":512,"num_inference_steps":20,"guidance_scale":7.5,"seed":42}'
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        assert resp.status == 200
        body = resp.read().decode()
    assert "presigned_url" in body or "image_base64" in body