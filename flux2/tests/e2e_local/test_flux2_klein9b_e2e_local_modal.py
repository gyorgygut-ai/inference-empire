"""E2E local tests for flux2 Modal worker.

Modal DI pattern: @app.cls replaces constructor.
Access raw class via FluxKleinWorker._get_user_cls(), call load(pipe=...) manually.
FakePipeline must include mock `torch` attribute for seed/generator support.
"""
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


def _make_raw_worker(monkeypatch, pipe=None):
    from worker_modal_cls_flux2_klein9b import FluxKleinWorker

    monkeypatch.setenv("R2_BUCKET", "generated-media")
    monkeypatch.setenv("R2_ENDPOINT", "https://test.r2.cloudflarestorage.com")
    monkeypatch.setenv("R2_ACCESS_KEY", "test-access")
    monkeypatch.setenv("R2_SECRET_KEY", "test-secret")
    monkeypatch.setenv("HF_TOKEN", "test-token")

    import boto3
    monkeypatch.setattr(boto3, "client", lambda *a, **kw: FakeS3())

    raw_cls = FluxKleinWorker._get_user_cls()
    raw = raw_cls()
    raw.load(pipe=pipe if pipe else FakePipeline())
    return raw


def test_e2e_generate_invalid_input_rejects(monkeypatch):
    raw = _make_raw_worker(monkeypatch)
    with pytest.raises(Exception):
        raw._run_generate(prompt=None)


def test_e2e_generate_good_inference_fail_returns_contract(monkeypatch):
    raw = _make_raw_worker(monkeypatch)

    class FailingPipeline:
        def __init__(self):
            self.torch = FakeTorch()
        def to(self, device):
            return self
        def __call__(self, **kw):
            raise RuntimeError("inference failed")

    raw.pipe = FailingPipeline()
    with pytest.raises(RuntimeError, match="inference failed"):
        raw._run_generate(prompt="a cat")


def test_e2e_generate_good_inference_success_returns_contract(monkeypatch):
    raw = _make_raw_worker(monkeypatch)
    result = raw._run_generate(prompt="a cat", seed=42)

    assert "artifact" in result
    assert result["artifact"]["url"].startswith("https://test.r2.cloudflarestorage.com/generated-media/")
    assert result["artifact"]["key"].startswith("flux2_") and result["artifact"]["key"].endswith(".png")
    assert result["artifact"]["size"] > 0


def test_e2e_generate_good_inference_success_uploads_artifact(monkeypatch):
    raw = _make_raw_worker(monkeypatch)
    result = raw._run_generate(prompt="a cat", seed=42)

    assert "artifact" in result
    assert result["artifact"]["url"].startswith("https://test.r2.cloudflarestorage.com/generated-media/")
    assert result["artifact"]["key"].startswith("flux2_") and result["artifact"]["key"].endswith(".png")
    assert result["artifact"]["size"] > 0
