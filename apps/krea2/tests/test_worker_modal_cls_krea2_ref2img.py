import io

import pytest
from PIL import Image
from pydantic import ValidationError

import apps.krea2.worker_modal_cls_krea2_ref2img as worker_mod
from apps._services.inference.image_pipe_fake import FakeImagePipe
from apps._services.torch_module.torch_module_fake import FakeTorchModule
from apps.krea2._shared_krea2_ref2img import Krea2Ref2ImgInput, Krea2Ref2ImgOutput, do_inference


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


def test_generate_returns_image_artifact(bucket):
    canned = Image.new("RGB", (8, 8), (255, 0, 0))
    out = worker_mod.generate(bucket, FakeImagePipe(canned), None, FakeTorchModule(), prompt="a red square", seed=7)
    assert bucket.fetch(out["artifact"]["presigned_url"].rsplit("/", 1)[-1]) == _png_bytes(canned)


def test_generate_rejects_missing_prompt(bucket):
    canned = Image.new("RGB", (8, 8), (255, 0, 0))
    with pytest.raises(ValidationError):
        worker_mod.generate(bucket, FakeImagePipe(canned), None, FakeTorchModule())


def test_load_dependencies_mocked(monkeypatch, bucket):
    canned = Image.new("RGB", (8, 8), (255, 0, 0))
    fake_pipe = FakeImagePipe(canned)
    fake_torch = FakeTorchModule()

    def fake_load(cache_dir=None):
        return bucket, fake_pipe, "/tmp/runtime", fake_torch

    monkeypatch.setattr(worker_mod, "load_dependencies", fake_load)
    storage, _pipe, _runtime_dir, _torch_mod = worker_mod.load_dependencies()
    assert storage is bucket
