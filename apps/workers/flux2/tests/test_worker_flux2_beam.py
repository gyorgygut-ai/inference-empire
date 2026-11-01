import importlib
import io
from types import SimpleNamespace

import pytest
from PIL import Image
from pydantic import ValidationError
from shared.fakes.image_pipe_fake import FakeImagePipe
from shared.fakes.torch_module_fake import FakeTorchModule

import apps.workers.flux2.worker_flux2_beam as worker_mod
from apps.workers.flux2.shared.worker_flux2 import (
    Flux2Klein9bInput,
    Flux2Klein9bOutput,
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
    req = Flux2Klein9bInput(prompt="a red square", seed=7)
    do_inference(spy, FakeTorchModule(), bucket, req)
    assert spy.kwargs["prompt"] == "a red square"
    assert spy.kwargs["num_inference_steps"] == 4
    assert spy.kwargs["guidance_scale"] == 1.0
    assert spy.kwargs["height"] == 512
    assert spy.kwargs["width"] == 512
    assert "generator" in spy.kwargs


def test_fake_bucket_has_uploaded_artifact(bucket):
    canned = Image.new("RGB", (8, 8), (255, 0, 0))
    spy = SpyPipe(canned)
    req = Flux2Klein9bInput(prompt="a red square", seed=7)
    out = do_inference(spy, FakeTorchModule(), bucket, req)
    key = out.artifact.presigned_url.rsplit("/", 1)[-1].split("?", 1)[0]
    assert bucket.fetch(key) == _png_bytes(canned)


def test_do_inference_returns_output_contract(bucket):
    canned = Image.new("RGB", (8, 8), (255, 0, 0))
    spy = SpyPipe(canned)
    req = Flux2Klein9bInput(prompt="a red square", seed=7)
    out = do_inference(spy, FakeTorchModule(), bucket, req)
    assert isinstance(out, Flux2Klein9bOutput)
    assert out.artifact.presigned_url.startswith("https://")


def test_generate_returns_image_artifact(bucket):
    canned = Image.new("RGB", (8, 8), (255, 0, 0))
    ctx = SimpleNamespace(on_start_value=(bucket, FakeImagePipe(canned), FakeTorchModule()))
    out = worker_mod.generate.local(ctx, prompt="a red square", seed=7)
    assert bucket.fetch(out["artifact"]["presigned_url"].rsplit("/", 1)[-1]) == _png_bytes(canned)


def test_generate_rejects_missing_prompt(bucket):
    canned = Image.new("RGB", (8, 8), (255, 0, 0))
    with pytest.raises(ValidationError):
        ctx = SimpleNamespace(on_start_value=(bucket, FakeImagePipe(canned), FakeTorchModule()))
        worker_mod.generate.local(ctx)


def test_load_dependencies_mocked(monkeypatch, bucket):
    canned = Image.new("RGB", (8, 8), (255, 0, 0))
    fake_pipe = FakeImagePipe(canned)
    fake_torch = FakeTorchModule()

    def fake_load():
        return bucket, fake_pipe, fake_torch

    monkeypatch.setattr(worker_mod, "load_dependencies", fake_load)
    storage, pipe, torch_mod = worker_mod.load_dependencies()
    assert storage is bucket
    assert pipe is fake_pipe
    assert torch_mod is fake_torch


def test_beam_generate_returns_image_artifact(monkeypatch, bucket):
    canned = Image.new("RGB", (8, 8), (255, 0, 0))
    ctx = SimpleNamespace(on_start_value=(bucket, FakeImagePipe(canned), FakeTorchModule()))
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
