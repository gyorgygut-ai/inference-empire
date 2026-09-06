import io
from types import SimpleNamespace

import pytest
from PIL import Image
from pydantic import ValidationError

import workers.flux2.worker_beam_tq_flux2_klein9b as worker_mod
from workers.services.inference.image_pipe_fake import FakeImagePipe
from workers.services.torch_module.torch_module_fake import FakeTorchModule


def _png_bytes(img):
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def test_generate_returns_image_artifact(bucket):
    canned = Image.new("RGB", (8, 8), (255, 0, 0))

    out = worker_mod.generate(
        bucket, FakeImagePipe(canned), FakeTorchModule(), prompt="a red square", seed=7
    )

    assert bucket.fetch(out["artifact"]["presigned_url"].rsplit("/", 1)[-1]) == _png_bytes(canned)


def test_generate_rejects_missing_prompt(bucket):
    canned = Image.new("RGB", (8, 8), (255, 0, 0))

    with pytest.raises(ValidationError):
        worker_mod.generate(bucket, FakeImagePipe(canned), FakeTorchModule())


def test_dispatch_returns_image_artifact(monkeypatch, bucket):
    canned = Image.new("RGB", (8, 8), (255, 0, 0))
    ctx = SimpleNamespace(on_start_value=(bucket, FakeImagePipe(canned), FakeTorchModule()))

    # .local runs the raw function; the decorator blocks direct calls.
    out = worker_mod.dispatch.local(ctx, prompt="a red square", seed=7)

    assert bucket.fetch(out["artifact"]["presigned_url"].rsplit("/", 1)[-1]) == _png_bytes(canned)
