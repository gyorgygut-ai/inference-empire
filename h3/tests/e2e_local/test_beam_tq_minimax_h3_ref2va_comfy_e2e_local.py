"""E2E local tests for h3 Beam ref2VA comfy worker.

Mock: requests (ComfyUI submit/poll/download), boto3 S3, time.sleep.
Tests full generate() flow.
"""
import base64
import time
from types import SimpleNamespace

import pytest


FAKE_VIDEO = b"\x00" * 1024


class FakeS3:
    def __init__(self, *a, **kw):
        pass

    def put_object(self, **kwargs):
        pass

    def generate_presigned_url(self, operation, Params, ExpiresIn):
        bucket = Params["Bucket"]
        key = Params["Key"]
        return f"https://test.r2.cloudflarestorage.com/{bucket}/{key}?X-Amz-Signature=fake"


class FakePostResponse:
    def __init__(self):
        self.status_code = 200

    def json(self):
        return {"prompt_id": "test-prompt-123"}

    def raise_for_status(self):
        pass


class FakeGetHistoryResponse:
    def __init__(self):
        self.status_code = 200

    def json(self):
        return {
            "test-prompt-123": {
                "outputs": {
                    "save": {
                        "videos": [
                            {
                                "filename": "MiniMax_H3_Ref2VA_00001.mp4",
                                "subfolder": "",
                                "type": "output",
                            }
                        ]
                    }
                }
            }
        }


class FakeGetVideoResponse:
    def __init__(self):
        self.content = FAKE_VIDEO


def _make_context():
    return SimpleNamespace(on_start_value="http://127.0.0.1:8188")


def _patch_requests(monkeypatch):
    import requests as req_mod

    def fake_post(url, json=None, timeout=None):
        return FakePostResponse()

    def fake_get(url, timeout=None):
        if "/history/" in url:
            return FakeGetHistoryResponse()
        elif "/view" in url:
            return FakeGetVideoResponse()
        return SimpleNamespace(status_code=404, json=lambda: {})

    monkeypatch.setattr(req_mod, "post", fake_post)
    monkeypatch.setattr(req_mod, "get", fake_get)


def test_e2e_generate_invalid_input_rejects(monkeypatch):
    _patch_requests(monkeypatch)
    import worker_beam_tq_minimax_h3_ref2va_comfy as mod

    ctx = _make_context()
    with pytest.raises(Exception):
        mod.generate(ctx, prompt=None)


def test_e2e_generate_good_inference_success_returns_contract(monkeypatch):
    _patch_requests(monkeypatch)

    import boto3
    monkeypatch.setattr(boto3, "client", lambda *a, **kw: FakeS3())
    monkeypatch.setenv("R2_BUCKET", "generated-media")
    monkeypatch.setenv("R2_ENDPOINT", "https://test.r2.cloudflarestorage.com")
    monkeypatch.setenv("R2_ACCESS_KEY", "test-access")
    monkeypatch.setenv("R2_SECRET_KEY", "test-secret")

    import worker_beam_tq_minimax_h3_ref2va_comfy as mod

    ctx = _make_context()
    result = mod.generate(ctx, prompt="a cat dancing", seed=42)

    assert "artifact" in result
    assert result["artifact"]["presigned_url"].startswith("https://test.r2.cloudflarestorage.com/generated-media/")


def test_e2e_generate_good_inference_success_uploads_artifact(monkeypatch):
    _patch_requests(monkeypatch)

    import boto3
    monkeypatch.setattr(boto3, "client", lambda *a, **kw: FakeS3())
    monkeypatch.setenv("R2_BUCKET", "generated-media")
    monkeypatch.setenv("R2_ENDPOINT", "https://test.r2.cloudflarestorage.com")
    monkeypatch.setenv("R2_ACCESS_KEY", "test-access")
    monkeypatch.setenv("R2_SECRET_KEY", "test-secret")

    import worker_beam_tq_minimax_h3_ref2va_comfy as mod

    ctx = _make_context()
    result = mod.generate(ctx, prompt="a cat dancing", seed=42)

    assert "artifact" in result
    assert result["artifact"]["presigned_url"].startswith("https://test.r2.cloudflarestorage.com/generated-media/")
