import importlib
import io
from types import SimpleNamespace

import pytest
from PIL import Image
from pydantic import ValidationError

import apps.workers.krea2.worker_krea2_beam as worker_mod
from apps.workers.krea2.fakes.image_pipe_fake import FakeImagePipe
from apps.workers.krea2.fakes.torch_module_fake import FakeTorchModule
from apps.workers.krea2.shared.worker_krea2 import (
    Krea2Ref2ImgInput,
    Krea2Ref2ImgOutput,
    do_inference,
)


def _png_bytes(img):
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


class SpyPipe(FakeImagePipe):
    def __init__(self, image):
        super().__init__(image)
        self.kwargs: dict = {}

    def __call__(self, **kwargs):
        self.kwargs = kwargs
        return super().__call__(**kwargs)


def test_do_inference_requested_with_right_args(bucket):
    canned = Image.new("RGB", (8, 8), (255, 0, 0))
    spy = SpyPipe(canned)
    req = Krea2Ref2ImgInput(prompt="a red square", seed=7)
    do_inference(spy, "/tmp/runtime", FakeTorchModule(), bucket, req)
    assert spy.kwargs["prompt"] == "a red square"
    assert spy.kwargs["num_inference_steps"] == 8
    assert spy.kwargs["guidance_scale"] == 0.0
    assert spy.kwargs["height"] == 768
    assert spy.kwargs["width"] == 768
    assert "generator" in spy.kwargs


def test_fake_bucket_has_uploaded_artifact(bucket):
    canned = Image.new("RGB", (8, 8), (255, 0, 0))
    spy = SpyPipe(canned)
    req = Krea2Ref2ImgInput(prompt="a red square", seed=7)
    out = do_inference(spy, "/tmp/runtime", FakeTorchModule(), bucket, req)
    key = out.artifact.presigned_url.rsplit("/", 1)[-1].split("?", 1)[0]
    assert bucket.fetch(key) == _png_bytes(canned)


def test_do_inference_returns_output_contract(bucket):
    canned = Image.new("RGB", (8, 8), (255, 0, 0))
    spy = SpyPipe(canned)
    req = Krea2Ref2ImgInput(prompt="a red square", seed=7)
    out = do_inference(spy, "/tmp/runtime", FakeTorchModule(), bucket, req)
    assert isinstance(out, Krea2Ref2ImgOutput)
    assert out.artifact.presigned_url.startswith("https://")


def test_generate_returns_image_artifact(bucket):
    canned = Image.new("RGB", (8, 8), (255, 0, 0))
    ctx = SimpleNamespace(on_start_value=(bucket, FakeImagePipe(canned), None, FakeTorchModule()))
    out = worker_mod.generate.local(ctx, prompt="a red square", seed=7)
    assert bucket.fetch(out["artifact"]["presigned_url"].rsplit("/", 1)[-1]) == _png_bytes(canned)


def test_generate_rejects_missing_prompt(bucket):
    canned = Image.new("RGB", (8, 8), (255, 0, 0))
    with pytest.raises(ValidationError):
        ctx = SimpleNamespace(on_start_value=(bucket, FakeImagePipe(canned), None, FakeTorchModule()))
        worker_mod.generate.local(ctx)


def test_load_dependencies_mocked(monkeypatch, bucket):
    canned = Image.new("RGB", (8, 8), (255, 0, 0))
    fake_pipe = FakeImagePipe(canned)
    fake_torch = FakeTorchModule()

    def fake_load(cache_dir=None):
        return bucket, fake_pipe, "/tmp/runtime", fake_torch

    monkeypatch.setattr(worker_mod, "load_dependencies", fake_load)
    storage, _pipe, _runtime_dir, _torch_mod = worker_mod.load_dependencies()
    assert storage is bucket
    assert _pipe is fake_pipe


def test_beam_generate_returns_image_artifact(monkeypatch, bucket):
    canned = Image.new("RGB", (8, 8), (255, 0, 0))
    ctx = SimpleNamespace(on_start_value=(bucket, FakeImagePipe(canned), "/tmp/runtime", FakeTorchModule()))
    out = worker_mod.generate.local(ctx, prompt="a red square", seed=7)
    assert bucket.fetch(out["artifact"]["presigned_url"].rsplit("/", 1)[-1]) == _png_bytes(canned)


def test_beam_image_receives_schema_runtime_environment(monkeypatch):
    expected = {
        "SECRET_HUGGINGFACE_TOKEN": "hf-sentinel",
        "SECRET_R2_ACCESS_KEY": "r2-access-sentinel",
        "SECRET_R2_SECRET_KEY": "r2-secret-sentinel",
        "SECRET_R2_ENDPOINT": "https://r2.invalid",
        "SECRET_R2_BUCKET": "bucket-sentinel",
    }
    for name, value in expected.items():
        monkeypatch.setenv(name, value)
    importlib.reload(worker_mod)
    configured = dict(line.split("=", 1) for line in worker_mod.image.env_vars)
    assert all(configured.get(name) == value for name, value in expected.items())
