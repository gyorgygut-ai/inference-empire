import io

import pytest
from PIL import Image
from pydantic import ValidationError

import workers.flux2.worker_modal_cls_flux2_klein9b as worker_mod
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


def test_init_stores_storage(monkeypatch, bucket):
    monkeypatch.setattr(worker_mod, "require_storage", lambda _s: bucket)

    worker = worker_mod.FluxKleinWorker()

    assert worker.storage is bucket
