"""E2E local tests for flux2 Beam worker.

Beam DI pattern: _run_generate is a module-level function, pipe is first param.
NOTE: Cloud-compute Beam SDK not installed locally; mock before import.
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

    def to(self, device):
        return self

    def __call__(self, prompt=None, height=512, width=512,
                 guidance_scale=1.0, num_inference_steps=4,
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
    if "worker_beam_tq_flux2_klein9b" in sys.modules:
        del sys.modules["worker_beam_tq_flux2_klein9b"]
    import worker_beam_tq_flux2_klein9b as mod
    return mod


def _mock_boto3(monkeypatch):
    import boto3
    monkeypatch.setattr(boto3, "client", lambda *a, **kw: FakeS3())


def test_e2e_generate_invalid_input_rejects(monkeypatch):
    mod = _import_worker()
    _make_env(monkeypatch)
    _mock_boto3(monkeypatch)
    with pytest.raises(Exception):
        mod._run_generate(pipe=FakePipeline(), prompt=None)


def test_e2e_generate_good_inference_fail_returns_contract(monkeypatch):
    mod = _import_worker()
    _make_env(monkeypatch)
    _mock_boto3(monkeypatch)

    class FailingPipeline:
        def __init__(self):
            self.torch = FakeTorch()
        def to(self, device):
            return self
        def __call__(self, **kw):
            raise RuntimeError("inference failed")

    with pytest.raises(RuntimeError, match="inference failed"):
        mod._run_generate(pipe=FailingPipeline(), prompt="a cat")


def test_e2e_generate_good_inference_success_returns_contract(monkeypatch):
    mod = _import_worker()
    _make_env(monkeypatch)
    _mock_boto3(monkeypatch)
    result = mod._run_generate(pipe=FakePipeline(), prompt="a cat", seed=42)

    assert "artifact" in result
    assert result["artifact"]["url"].startswith("https://test.r2.cloudflarestorage.com/generated-media/")
    assert result["artifact"]["key"].startswith("flux2_") and result["artifact"]["key"].endswith(".png")
    assert result["artifact"]["size"] > 0


def test_e2e_generate_good_inference_success_uploads_artifact(monkeypatch):
    mod = _import_worker()
    _make_env(monkeypatch)
    _mock_boto3(monkeypatch)
    result = mod._run_generate(pipe=FakePipeline(), prompt="a cat", seed=42)

    assert "artifact" in result
    assert result["artifact"]["url"].startswith("https://test.r2.cloudflarestorage.com/generated-media/")
    assert result["artifact"]["key"].startswith("flux2_") and result["artifact"]["key"].endswith(".png")
    assert result["artifact"]["size"] > 0
