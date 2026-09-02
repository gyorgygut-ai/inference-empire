"""Unit tests for krea2 Beam worker - testing Input/Output schemas and _run_generate() only.

Beam DI pattern: _run_generate is a module-level function, pipe/runtime_dir/torch are first params.
Call _run_generate(pipe, runtime_dir, torch, ...) directly.

NOTE: The cloud-compute Beam SDK is not installed locally. We mock the beam module
before importing the worker to avoid import errors.
"""
import sys
import types
import pytest
from PIL import Image


class FakeTorch:
    class Generator:
        def __init__(self, device=None):
            pass
        def manual_seed(self, seed):
            return self


class FakePipeline:
    def __init__(self, model_id=None, **kwargs):
        self.model_id = model_id
        self.kwargs = kwargs
        self.torch = FakeTorch()

    def set_adapters(self, adapters, weights):
        pass

    def __call__(self, prompt=None, height=768, width=768,
                 guidance_scale=0.0, num_inference_steps=8,
                 generator=None, image=None, **kwargs):
        fake_img = Image.new("RGB", (width, height), color="red")
        class FakeOutput:
            images = [fake_img]
        return FakeOutput()


class FakeS3:
    def put_object(self, **kwargs):
        pass

    def generate_presigned_url(self, operation, Params, ExpiresIn):
        bucket = Params["Bucket"]
        key = Params["Key"]
        return f"https://test.r2.cloudflarestorage.com/{bucket}/{key}?X-Amz-Signature=fake"


class FakeRuntimeDir:
    def glob(self, pattern):
        return []


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

    beam_mock.Image = FakeImage
    beam_mock.QueueDepthAutoscaler = type("QueueDepthAutoscaler", (), {"__init__": lambda s, **kw: None})
    beam_mock.Volume = type("Volume", (), {"__init__": lambda s, **kw: None})
    beam_mock.task_queue = lambda **kw: lambda f: f
    return beam_mock


def _ensure_beam_mocked():
    if "beam" not in sys.modules or not hasattr(sys.modules["beam"], "QueueDepthAutoscaler"):
        sys.modules["beam"] = _mock_beam()


def _make_env(monkeypatch):
    monkeypatch.setenv("R2_BUCKET", "generated-media")
    monkeypatch.setenv("R2_ENDPOINT", "https://test.r2.cloudflarestorage.com")
    monkeypatch.setenv("R2_ACCESS_KEY", "test-access")
    monkeypatch.setenv("R2_SECRET_KEY", "test-secret")
    monkeypatch.setenv("HF_TOKEN", "test-token")


def _import_worker():
    _ensure_beam_mocked()
    if "worker_beam_tq_krea2_ref2img" in sys.modules:
        del sys.modules["worker_beam_tq_krea2_ref2img"]
    import worker_beam_tq_krea2_ref2img as mod
    return mod


def _mock_boto3(monkeypatch):
    import boto3
    monkeypatch.setattr(boto3, "client", lambda *a, **kw: FakeS3())


def test_generate_invalid_input(monkeypatch):
    mod = _import_worker()
    _make_env(monkeypatch)
    _mock_boto3(monkeypatch)
    with pytest.raises(Exception):
        mod._run_generate(pipe=FakePipeline(), runtime_dir=FakeRuntimeDir(), torch=FakeTorch(), prompt=None)


def test_generate_good_succeeded(monkeypatch):
    mod = _import_worker()
    _make_env(monkeypatch)
    _mock_boto3(monkeypatch)
    result = mod._run_generate(pipe=FakePipeline(), runtime_dir=FakeRuntimeDir(), torch=FakeTorch(),
                                prompt="a cat", seed=42)

    assert "artifact" in result
    assert result["artifact"]["presigned_url"].startswith("https://test.r2.cloudflarestorage.com/generated-media/")


def test_generate_good_but_failed(monkeypatch):
    mod = _import_worker()
    _make_env(monkeypatch)
    _mock_boto3(monkeypatch)

    class FailingPipeline:
        def __init__(self):
            self.torch = FakeTorch()
        def set_adapters(self, adapters, weights):
            pass
        def __call__(self, **kw):
            raise RuntimeError("inference failed")

    with pytest.raises(RuntimeError, match="inference failed"):
        mod._run_generate(pipe=FailingPipeline(), runtime_dir=FakeRuntimeDir(), torch=FakeTorch(),
                          prompt="a cat")


def test_generate_good_inference_success_uploads_artifact(monkeypatch):
    mod = _import_worker()
    _make_env(monkeypatch)
    _mock_boto3(monkeypatch)
    result = mod._run_generate(pipe=FakePipeline(), runtime_dir=FakeRuntimeDir(), torch=FakeTorch(),
                                prompt="a cat", seed=42)

    assert "artifact" in result
    assert result["artifact"]["presigned_url"].startswith("https://test.r2.cloudflarestorage.com/generated-media/")