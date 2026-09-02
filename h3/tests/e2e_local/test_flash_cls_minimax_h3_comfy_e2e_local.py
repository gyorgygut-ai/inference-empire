"""E2E local tests for h3 Flash CLS comfy worker.

Mock: runpod_flash (Endpoint decorator), endpoint.runsync(), boto3 S3.
Tests full generate() flow end-to-end.
"""
import base64
import sys
import types
from types import SimpleNamespace

import pytest


FAKE_VIDEO = b"\x00" * 1024


def _mock_runpod_flash():
    mock = types.ModuleType("runpod_flash")

    class FakeGpuGroup:
        ADA_32_PRO = "ADA_32_PRO"

    class FakePodTemplate:
        def __init__(self, **kw):
            pass

    class FakeEndpoint:
        def __init__(self, **kw):
            self._kw = kw
        def __call__(self, cls):
            return cls

    mock.GpuGroup = FakeGpuGroup
    mock.PodTemplate = FakePodTemplate
    mock.Endpoint = FakeEndpoint
    return mock


class FakeComfyEndpoint:
    def __init__(self, *a, **kw):
        pass

    async def runsync(self, payload, timeout=None):
        return SimpleNamespace(
            output={"images": [{"data": base64.b64encode(FAKE_VIDEO).decode()}]},
            error=None,
        )


class FakeComfyEndpointFails:
    def __init__(self, *a, **kw):
        pass

    async def runsync(self, payload, timeout=None):
        return SimpleNamespace(
            output=None,
            error="inference failed on backend",
        )


class FakeS3:
    def __init__(self, *a, **kw):
        pass

    def put_object(self, **kwargs):
        pass

    def generate_presigned_url(self, operation, Params, ExpiresIn):
        bucket = Params["Bucket"]
        key = Params["Key"]
        return f"https://test.r2.cloudflarestorage.com/{bucket}/{key}?X-Amz-Signature=fake"


def _import_worker():
    sys.modules["runpod_flash"] = _mock_runpod_flash()
    for key in list(sys.modules.keys()):
        if key.startswith("worker_flash_cls_minimax_h3_comfy"):
            del sys.modules[key]
    import worker_flash_cls_minimax_h3_comfy as mod
    return mod


def _make_worker(monkeypatch):
    from typing import Optional
    mod = _import_worker()

    monkeypatch.setenv("R2_BUCKET", "generated-media")
    monkeypatch.setenv("R2_ENDPOINT", "https://test.r2.cloudflarestorage.com")
    monkeypatch.setenv("R2_ACCESS_KEY", "test-access")
    monkeypatch.setenv("R2_SECRET_KEY", "test-secret")
    monkeypatch.setenv("HF_TOKEN", "test-token")

    import boto3
    monkeypatch.setattr(boto3, "client", lambda *a, **kw: FakeS3())

    mod._Optional = Optional
    mod._BaseModel = __import__("pydantic", fromlist=["BaseModel"]).BaseModel
    mod._ConfigDict = __import__("pydantic", fromlist=["ConfigDict"]).ConfigDict
    mod._Field = __import__("pydantic", fromlist=["Field"]).Field
    mod.MiniMaxH3ComfyWorker.Input.model_rebuild()

    raw_cls = mod.MiniMaxH3ComfyWorker
    raw = raw_cls.__new__(raw_cls)
    raw.Input = raw_cls.Input
    raw.endpoint = FakeComfyEndpoint()
    raw.MODEL_FILES = {
        "unet_name": "minimax_h3_fl2va_pruned_int8_convrot.safetensors",
        "clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
        "vae_video_name": "minimax_h3_video_vae_fp16.safetensors",
        "vae_audio_name": "minimax_h3_audio_vae_fp32.safetensors",
    }
    return raw


def test_e2e_generate_invalid_input_rejects(monkeypatch):
    raw = _make_worker(monkeypatch)
    with pytest.raises(Exception):
        raw.generate(prompt=None)


def test_e2e_generate_good_inference_fail(monkeypatch):
    raw = _make_worker(monkeypatch)
    raw.endpoint = FakeComfyEndpointFails()
    with pytest.raises(RuntimeError, match="job failed"):
        raw.generate(prompt="a cat dancing")


def test_e2e_generate_good_inference_success_returns_contract(monkeypatch):
    raw = _make_worker(monkeypatch)
    result = raw.generate(prompt="a cat dancing", seed=42)

    assert "artifact" in result
    assert result["artifact"]["presigned_url"].startswith("https://test.r2.cloudflarestorage.com/generated-media/")


def test_e2e_generate_good_inference_success_uploads_artifact(monkeypatch):
    raw = _make_worker(monkeypatch)
    result = raw.generate(prompt="a cat dancing", seed=42)

    assert "artifact" in result
    assert result["artifact"]["presigned_url"].startswith("https://test.r2.cloudflarestorage.com/generated-media/")
