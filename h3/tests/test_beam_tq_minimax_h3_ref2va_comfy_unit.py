"""Unit tests for h3 Beam ref2va comfy worker — testing Input schema, validators, _build_workflow(), _build_images(), and generate().

Beam DI pattern: module-level functions, pipe via context.on_start_value.
The cloud-compute Beam SDK is not installed locally. We mock the beam module
before importing the worker to avoid import errors.
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


def _mock_beam():
    beam_mock = types.ModuleType("beam")

    class FakeImage:
        def __init__(self, **kw):
            pass
        def add_python_packages(self, pkgs):
            return self
        def with_envs(self, envs):
            return self
        def add_commands(self, cmds):
            return self
        @staticmethod
        def from_registry(*a, **kw):
            return FakeImage()

    beam_mock.Image = FakeImage
    beam_mock.QueueDepthAutoscaler = type("QueueDepthAutoscaler", (), {"__init__": lambda s, **kw: None})
    beam_mock.Volume = type("Volume", (), {"__init__": lambda s, **kw: None})
    beam_mock.task_queue = lambda **kw: lambda f: f
    return beam_mock


def _ensure_beam_mocked():
    if "beam" not in sys.modules or not hasattr(sys.modules["beam"], "QueueDepthAutoscaler"):
        sys.modules["beam"] = _mock_beam()


def _import_worker():
    _ensure_beam_mocked()
    for key in list(sys.modules.keys()):
        if key.startswith("worker_beam_tq_minimax_h3_ref2va_comfy"):
            del sys.modules[key]
    import worker_beam_tq_minimax_h3_ref2va_comfy as mod
    return mod


def _make_env(monkeypatch):
    monkeypatch.setenv("R2_BUCKET", "generated-media")
    monkeypatch.setenv("R2_ENDPOINT", "https://test.r2.cloudflarestorage.com")
    monkeypatch.setenv("R2_ACCESS_KEY", "test-access")
    monkeypatch.setenv("R2_SECRET_KEY", "test-secret")
    monkeypatch.setenv("HF_TOKEN", "test-token")


def _mock_boto3(monkeypatch):
    import boto3
    monkeypatch.setattr(boto3, "client", lambda *a, **kw: FakeS3())


def _mock_requests(monkeypatch):
    import requests as req_mod

    class FakeResponse:
        def __init__(self, json_data=None, status_code=200, content=b""):
            self._json = json_data
            self.status_code = status_code
            self.content = content
        def json(self):
            return self._json
        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP {self.status_code}")

    def fake_post(url, json=None, timeout=None):
        return FakeResponse(json_data={"prompt_id": "test-prompt-id"}, status_code=200)

    def fake_get(url, timeout=None):
        if "/history/" in url:
            return FakeResponse(json_data={
                "test-prompt-id": {
                    "outputs": {
                        "save": {
                            "videos": [{"filename": "test.mp4", "subfolder": "", "type": "output"}]
                        }
                    }
                }
            })
        if "/view?" in url:
            return FakeResponse(content=b"\x00" * 100, status_code=200)
        return FakeResponse(json_data={}, status_code=200)

    monkeypatch.setattr(req_mod, "post", fake_post)
    monkeypatch.setattr(req_mod, "get", fake_get)


def test_generate_invalid_input(monkeypatch):
    mod = _import_worker()
    _make_env(monkeypatch)
    _mock_boto3(monkeypatch)
    _mock_requests(monkeypatch)
    with pytest.raises(Exception):
        mod.generate(
            context=SimpleNamespace(on_start_value="http://127.0.0.1:8188"),
            prompt=None,
        )


def test_generate_good_succeeded(monkeypatch):
    mod = _import_worker()
    _make_env(monkeypatch)
    _mock_boto3(monkeypatch)
    _mock_requests(monkeypatch)
    result = mod.generate(
        context=SimpleNamespace(on_start_value="http://127.0.0.1:8188"),
        prompt="a cat dancing",
        seed=42,
    )
    assert "artifact" in result
    assert result["artifact"]["presigned_url"].startswith("https://test.r2.cloudflarestorage.com/generated-media/")


def test_validate_too_many_ref_images(monkeypatch):
    mod = _import_worker()
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        mod.ValidatedInput(prompt="a cat", ref_images=["img"] * 10)


def test_validate_too_many_ref_videos(monkeypatch):
    mod = _import_worker()
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        mod.ValidatedInput(prompt="a cat", ref_videos=["vid"] * 4)


def test_validate_ref_video_audios_exceed_videos(monkeypatch):
    mod = _import_worker()
    with pytest.raises(ValueError, match="reference video audio tracks for .* reference videos"):
        mod.ValidatedInput(
            prompt="a cat",
            ref_videos=["vid1"],
            ref_video_audios=["aud1", "aud2"],
        )


def test_validate_audio_without_visual(monkeypatch):
    mod = _import_worker()
    with pytest.raises(ValueError, match="reference audio requires at least one reference image or video"):
        mod.ValidatedInput(prompt="a cat", ref_audios=["aud1"])


def test_validate_total_refs_exceed_12(monkeypatch):
    mod = _import_worker()
    with pytest.raises(ValueError, match="too many reference files in total"):
        mod.ValidatedInput(
            prompt="a cat",
            ref_images=["img"] * 9,
            ref_videos=["vid"] * 3,
            ref_audios=["aud"] * 1,
        )


def test_build_workflow_no_refs(monkeypatch):
    mod = _import_worker()
    req = mod.ValidatedInput(prompt="a cat", width=1344, height=768, length=124, steps=20, seed=42)
    workflow = mod._build_workflow(req)

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
    mod = _import_worker()
    req = mod.ValidatedInput(
        prompt="a cat",
        ref_images=["img1", "img2"],
        ref_videos=["vid1"],
        ref_video_audios=["aud1"],
        ref_audios=["aud2"],
    )
    workflow = mod._build_workflow(req)

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
    mod = _import_worker()
    req = mod.ValidatedInput(
        prompt="a cat",
        ref_images=["img1b64", "img2b64"],
        ref_videos=["vid1b64"],
        ref_video_audios=["aud1b64"],
        ref_audios=["aud2b64"],
    )
    images = mod._build_images(req)

    assert len(images) == 5
    assert images[0] == {"name": "ref_image_1.png", "image": "data:image/png;base64,img1b64"}
    assert images[1] == {"name": "ref_image_2.png", "image": "data:image/png;base64,img2b64"}
    assert images[2] == {"name": "ref_video_1.mp4", "image": "data:video/mp4;base64,vid1b64"}
    assert images[3] == {"name": "ref_video_audio_1.mp3", "image": "data:audio/mp3;base64,aud1b64"}
    assert images[4] == {"name": "ref_audio_1.mp3", "image": "data:audio/mp3;base64,aud2b64"}
