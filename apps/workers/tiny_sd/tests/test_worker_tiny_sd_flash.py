import io

import pytest
from fakes.image_pipe_fake import FakeImagePipe
from fakes.torch_module_fake import FakeTorchModule
from PIL import Image
from pydantic import ValidationError
from shared.worker_tiny_sd import TinySDInput, TinySDOutput, do_inference

import apps.workers.tiny_sd.worker_tiny_sd_flash as worker_mod


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
    canned = Image.new("RGB", (8, 8), (128, 128, 128))
    spy = SpyPipe(canned)
    req = TinySDInput(prompt="a tiny square", seed=42)
    do_inference(spy, FakeTorchModule(), bucket, req)
    assert spy.kwargs["prompt"] == "a tiny square"
    assert spy.kwargs["num_inference_steps"] == 20
    assert spy.kwargs["guidance_scale"] == 7.5


def test_fake_bucket_has_uploaded_artifact(bucket):
    canned = Image.new("RGB", (8, 8), (128, 128, 128))
    spy = SpyPipe(canned)
    req = TinySDInput(prompt="a tiny square", seed=42)
    out = do_inference(spy, FakeTorchModule(), bucket, req)
    key = out.artifact.presigned_url.rsplit("/", 1)[-1].split("?", 1)[0]
    assert bucket.fetch(key) == _png_bytes(canned)


def test_do_inference_returns_output_contract(bucket):
    canned = Image.new("RGB", (8, 8), (128, 128, 128))
    spy = SpyPipe(canned)
    req = TinySDInput(prompt="a tiny square", seed=42)
    out = do_inference(spy, FakeTorchModule(), bucket, req)
    assert isinstance(out, TinySDOutput)


def test_generate_returns_image_artifact(bucket):
    canned = Image.new("RGB", (8, 8), (128, 128, 128))
    out = do_inference(FakeImagePipe(canned), FakeTorchModule(), bucket, TinySDInput(prompt="a tiny square", seed=42)).model_dump()
    assert bucket.fetch(out["artifact"]["presigned_url"].rsplit("/", 1)[-1]) == _png_bytes(canned)


def test_generate_rejects_missing_prompt(bucket):
    with pytest.raises(ValidationError):
        TinySDInput.model_validate({})


def test_load_dependencies_mocked(monkeypatch, bucket):
    canned = Image.new("RGB", (8, 8), (128, 128, 128))
    fake_pipe = FakeImagePipe(canned)
    fake_torch = FakeTorchModule()

    def fake_load():
        return bucket, fake_pipe, fake_torch

    monkeypatch.setattr(worker_mod, "load_dependencies", fake_load)
    storage, _pipe, _torch_mod = worker_mod.load_dependencies()
    assert storage is bucket
