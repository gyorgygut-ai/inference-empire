"""Acceptance test for worker-krea2.

Runs after deploy-beam; proves the deployed worker serves a request.
"""
import os
import urllib.request

import pytest


def test_worker_krea2_acceptance():
    """Ping the deployed worker-krea2 and assert it returns a valid contract."""
    url = os.environ["SECRET_WORKER_KREA2_URL"]
    payload = b'{"prompt":"a red square","negative_prompt":"","width":256,"height":256,"num_inference_steps":8,"guidance_scale":0.0,"seed":7}'
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        assert resp.status == 200
        body = resp.read().decode()
    assert "presigned_url" in body or "text" in body