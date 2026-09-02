"""Unit tests for h3 Flash comfy worker — testing Input schema, _build_workflow(), _build_images(), and generate().

Flash DI pattern: RemoteClassWrapper blocks _-prefixed methods.
Access raw class via w._class_type, inject forward ref types, call model_rebuild().
"""
import sys
import types
import pytest
from types import SimpleNamespace
from PIL import Image


FAKE_B64_VIDEO = "dGVzdA=="  # base64("test")


class FakeS3:
    def put_object(self, **kwargs):
        pass

    def generate_presigned_url(self, operation, Params, ExpiresIn):
        bucket = Params["Bucket"]
        key = Params["Key"]
        return f"https://test.r2.cloudflarestorage.com/{bucket}/{key}?X-Amz-Signature=fake"


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


def _ensure_runpod_mocked():
    sys.modules["runpod_flash"] = _mock_runpod_flash()


def _import_worker():
    _ensure_runpod_mocked()
    for key in list(sys.modules.keys()):
        if key.startswith("worker_flash_cls_minimax_h3_comfy"):
            del sys.modules[key]
    import worker_flash_cls_minimax_h3_comfy as mod
    return mod


def _make_raw_worker(monkeypatch, endpoint_runsync_result=None):
    mod = _import_worker()

    monkeypatch.setenv("R2_BUCKET", "generated-media")
    monkeypatch.setenv("R2_ENDPOINT", "https://test.r2.cloudflarestorage.com")
    monkeypatch.setenv("R2_ACCESS_KEY", "test-access")
    monkeypatch.setenv("R2_SECRET_KEY", "test-secret")
    monkeypatch.setenv("HF_TOKEN", "test-token")

    import boto3
    monkeypatch.setattr(boto3, "client", lambda *a, **kw: FakeS3())

    raw = mod.MiniMaxH3ComfyWorker.__new__(mod.MiniMaxH3ComfyWorker)

    from typing import Optional
    mod._Optional = Optional
    mod._BaseModel = __import__("pydantic", fromlist=["BaseModel"]).BaseModel
    mod._ConfigDict = __import__("pydantic", fromlist=["ConfigDict"]).ConfigDict
    mod._Field = __import__("pydantic", fromlist=["Field"]).Field
    mod.MiniMaxH3ComfyWorker.Input.model_rebuild()

    raw.Input = mod.MiniMaxH3ComfyWorker.Input
    raw.MODEL_FILES = {
        "unet_name": "minimax_h3_fl2va_pruned_int8_convrot.safetensors",
        "clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
        "vae_video_name": "minimax_h3_video_vae_fp16.safetensors",
        "vae_audio_name": "minimax_h3_audio_vae_fp32.safetensors",
    }

    class FakeComfyEndpoint:
        async def runsync(self, payload, timeout=None):
            return SimpleNamespace(
                output={"images": [{"data": FAKE_B64_VIDEO}]},
                error=None,
            )

    raw.endpoint = FakeComfyEndpoint()
    return raw, mod


def test_generate_invalid_input(monkeypatch):
    raw, mod = _make_raw_worker(monkeypatch)
    with pytest.raises(Exception):
        raw.generate(prompt=None)


def test_generate_good_succeeded(monkeypatch):
    raw, mod = _make_raw_worker(monkeypatch)
    result = raw.generate(prompt="a cat dancing", seed=42)
    assert "artifact" in result
    assert result["artifact"]["presigned_url"].startswith("https://test.r2.cloudflarestorage.com/generated-media/")


def test_generate_inference_fail(monkeypatch):
    raw, mod = _make_raw_worker(monkeypatch)

    class FailingEndpoint:
        async def runsync(self, payload, timeout=None):
            raise RuntimeError("ComfyUI inference failed")

    raw.endpoint = FailingEndpoint()
    with pytest.raises(RuntimeError, match="ComfyUI inference failed"):
        raw.generate(prompt="a cat")


def test_build_workflow_no_frames(monkeypatch):
    raw, mod = _make_raw_worker(monkeypatch)
    req = raw.Input(prompt="a cat", width=1344, height=768, length=124, steps=20, seed=42)
    workflow = raw._build_workflow(req)

    assert workflow["unet"]["class_type"] == "UNETLoader"
    assert workflow["clip"]["class_type"] == "CLIPLoader"
    assert workflow["vae_video"]["class_type"] == "VAELoader"
    assert workflow["vae_audio"]["class_type"] == "VAELoader"
    assert workflow["cond"]["class_type"] == "MiniMaxH3ImageToVideo"
    assert workflow["cond"]["inputs"]["prompt"] == "a cat"
    assert workflow["cond"]["inputs"]["width"] == 1344
    assert workflow["cond"]["inputs"]["height"] == 768
    assert workflow["cond"]["inputs"]["length"] == 124
    assert workflow["noise"]["inputs"]["noise_seed"] == 42
    assert workflow["sigmas"]["inputs"]["steps"] == 20
    assert workflow["save"]["class_type"] == "SaveVideo"

    assert "load_first" not in workflow
    assert "load_last" not in workflow


def test_build_workflow_with_first_frame(monkeypatch):
    raw, mod = _make_raw_worker(monkeypatch)
    req = raw.Input(prompt="a cat", first_frame="AAAA", seed=42)
    workflow = raw._build_workflow(req)

    assert "load_first" in workflow
    assert workflow["load_first"]["class_type"] == "LoadImage"
    assert workflow["cond"]["inputs"]["first_frame"] == ["load_first", 0]
    assert "load_last" not in workflow


def test_build_workflow_with_last_frame(monkeypatch):
    raw, mod = _make_raw_worker(monkeypatch)
    req = raw.Input(prompt="a cat", last_frame="BBBB", seed=42)
    workflow = raw._build_workflow(req)

    assert "load_last" in workflow
    assert workflow["load_last"]["class_type"] == "LoadImage"
    assert workflow["cond"]["inputs"]["last_frame"] == ["load_last", 0]
    assert "load_first" not in workflow


def test_build_workflow_with_both_frames(monkeypatch):
    raw, mod = _make_raw_worker(monkeypatch)
    req = raw.Input(prompt="a cat", first_frame="AAAA", last_frame="BBBB", seed=42)
    workflow = raw._build_workflow(req)

    assert "load_first" in workflow
    assert "load_last" in workflow
    assert workflow["cond"]["inputs"]["first_frame"] == ["load_first", 0]
    assert workflow["cond"]["inputs"]["last_frame"] == ["load_last", 0]


def test_build_images_no_frames(monkeypatch):
    raw, mod = _make_raw_worker(monkeypatch)
    req = raw.Input(prompt="a cat")
    images = raw._build_images(req)
    assert images == []


def test_build_images_with_frames(monkeypatch):
    raw, mod = _make_raw_worker(monkeypatch)
    req = raw.Input(prompt="a cat", first_frame="AAAA", last_frame="BBBB")
    images = raw._build_images(req)

    assert len(images) == 2
    assert images[0]["name"] == "first_frame.png"
    assert images[0]["image"] == "data:image/png;base64,AAAA"
    assert images[1]["name"] == "last_frame.png"
    assert images[1]["image"] == "data:image/png;base64,BBBB"
