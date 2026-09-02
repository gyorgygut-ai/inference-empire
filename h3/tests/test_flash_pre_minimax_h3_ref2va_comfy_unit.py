"""Unit tests for h3 Flash ref2va comfy worker — testing Input schema, validators, _build_workflow(), _build_images(), and generate().

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
        if key.startswith("worker_flash_pre_minimax_h3_ref2va_comfy"):
            del sys.modules[key]
    import worker_flash_pre_minimax_h3_ref2va_comfy as mod
    return mod


def _make_raw_worker(monkeypatch):
    mod = _import_worker()

    monkeypatch.setenv("R2_BUCKET", "generated-media")
    monkeypatch.setenv("R2_ENDPOINT", "https://test.r2.cloudflarestorage.com")
    monkeypatch.setenv("R2_ACCESS_KEY", "test-access")
    monkeypatch.setenv("R2_SECRET_KEY", "test-secret")
    monkeypatch.setenv("HF_TOKEN", "test-token")

    import boto3
    monkeypatch.setattr(boto3, "client", lambda *a, **kw: FakeS3())

    raw = mod.MiniMaxH3Ref2VAComfyWorker.__new__(mod.MiniMaxH3Ref2VAComfyWorker)

    from typing import Optional, Literal
    mod._Optional = Optional
    mod._Literal = Literal
    mod._BaseModel = __import__("pydantic", fromlist=["BaseModel"]).BaseModel
    mod._ConfigDict = __import__("pydantic", fromlist=["ConfigDict"]).ConfigDict
    mod._Field = __import__("pydantic", fromlist=["Field"]).Field
    mod.MiniMaxH3Ref2VAComfyWorker.Input.model_rebuild()

    raw.MODEL_FILES = {
        "unet_name": "minimax_h3_ref2va_pruned_int8_convrot.safetensors",
        "clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
        "vae_video_name": "minimax_h3_video_vae_fp16.safetensors",
        "vae_audio_name": "minimax_h3_audio_vae_fp32.safetensors",
    }

    raw.__init__()

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


def test_validate_too_many_ref_images(monkeypatch):
    raw, mod = _make_raw_worker(monkeypatch)
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        raw.Input(prompt="a cat", ref_images=["img"] * 10)


def test_validate_too_many_ref_videos(monkeypatch):
    raw, mod = _make_raw_worker(monkeypatch)
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        raw.Input(prompt="a cat", ref_videos=["vid"] * 4)


def test_validate_ref_video_audios_exceed_videos(monkeypatch):
    raw, mod = _make_raw_worker(monkeypatch)
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        raw.Input(
            prompt="a cat",
            ref_videos=["vid1"],
            ref_video_audios=["aud1", "aud2"],
        )


def test_validate_audio_without_visual(monkeypatch):
    raw, mod = _make_raw_worker(monkeypatch)
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        raw.Input(prompt="a cat", ref_audios=["aud1"])


def test_validate_total_refs_exceed_12(monkeypatch):
    raw, mod = _make_raw_worker(monkeypatch)
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        raw.Input(
            prompt="a cat",
            ref_images=["img"] * 9,
            ref_videos=["vid"] * 3,
            ref_audios=["aud"] * 1,
        )


def test_validate_valid_refs(monkeypatch):
    raw, mod = _make_raw_worker(monkeypatch)
    req = raw.Input(
        prompt="a cat",
        ref_images=["img1", "img2"],
        ref_videos=["vid1"],
        ref_video_audios=["aud1"],
        ref_audios=["aud2"],
    )
    assert req.prompt == "a cat"
    assert len(req.ref_images) == 2
    assert len(req.ref_videos) == 1
    assert len(req.ref_video_audios) == 1
    assert len(req.ref_audios) == 1


def test_build_workflow_no_refs(monkeypatch):
    raw, mod = _make_raw_worker(monkeypatch)
    req = raw.Input(prompt="a cat", width=1344, height=768, length=124, steps=20, seed=42)
    workflow = raw._build_workflow(req)

    assert workflow["cond"]["class_type"] == "MiniMaxH3ReferenceToVideo"
    assert workflow["cond"]["inputs"]["prompt"] == "a cat"
    assert workflow["cond"]["inputs"]["width"] == 1344
    assert workflow["cond"]["inputs"]["height"] == 768
    assert workflow["cond"]["inputs"]["length"] == 124
    assert workflow["cond"]["inputs"]["ref_image_size"] == "match"
    assert workflow["noise"]["inputs"]["noise_seed"] == 42
    assert workflow["sigmas"]["inputs"]["steps"] == 20
    assert workflow["sigmas"]["inputs"]["scheduler"] == "simple"
    assert workflow["save"]["class_type"] == "SaveVideo"

    for key in workflow:
        if key.startswith("load_ref"):
            pytest.fail(f"Unexpected ref node {key} in workflow")


def test_build_workflow_with_refs(monkeypatch):
    raw, mod = _make_raw_worker(monkeypatch)
    req = raw.Input(
        prompt="a cat",
        ref_images=["img1", "img2"],
        ref_videos=["vid1"],
        ref_video_audios=["aud1"],
        ref_audios=["aud2"],
    )
    workflow = raw._build_workflow(req)

    assert "load_ref_image_1" in workflow
    assert "load_ref_image_2" in workflow
    assert "load_ref_video_1" in workflow
    assert "load_ref_audio_1" in workflow

    assert workflow["load_ref_image_1"]["class_type"] == "LoadImage"
    assert workflow["load_ref_video_1"]["class_type"] == "LoadVideo"
    assert workflow["load_ref_audio_1"]["class_type"] == "LoadAudio"

    assert workflow["cond"]["inputs"]["ref_image_1"] == ["load_ref_image_1", 0]
    assert workflow["cond"]["inputs"]["ref_image_2"] == ["load_ref_image_2", 0]
    assert workflow["cond"]["inputs"]["ref_video_1"] == ["load_ref_video_1", 0]
    assert workflow["cond"]["inputs"]["ref_video_audio_1"] == ["load_ref_video_1", 1]
    assert workflow["cond"]["inputs"]["ref_audio_1"] == ["load_ref_audio_1", 0]


def test_build_images_with_refs(monkeypatch):
    raw, mod = _make_raw_worker(monkeypatch)
    req = raw.Input(
        prompt="a cat",
        ref_images=["img1b64", "img2b64"],
        ref_videos=["vid1b64"],
        ref_video_audios=["aud1b64"],
        ref_audios=["aud2b64"],
    )
    images = raw._build_images(req)

    assert len(images) == 5
    assert images[0] == {"name": "ref_image_1.png", "image": "data:image/png;base64,img1b64"}
    assert images[1] == {"name": "ref_image_2.png", "image": "data:image/png;base64,img2b64"}
    assert images[2] == {"name": "ref_video_1.mp4", "image": "data:video/mp4;base64,vid1b64"}
    assert images[3] == {"name": "ref_video_audio_1.mp3", "image": "data:audio/mp3;base64,aud1b64"}
    assert images[4] == {"name": "ref_audio_1.mp3", "image": "data:audio/mp3;base64,aud2b64"}
