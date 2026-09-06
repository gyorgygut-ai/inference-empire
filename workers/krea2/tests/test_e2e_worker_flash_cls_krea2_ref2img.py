import io

import pytest
from PIL import Image

import workers.krea2.worker_flash_cls_krea2_ref2img as worker_mod
from workers.services.inference.image_pipe_fake import FakeImagePipe
from workers.services.torch_module.torch_module_fake import FakeTorchModule


def _png_bytes(img):
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.local_e2e
def test_e2e_flash_generate_returns_image_artifact(e2e_target, bucket):
    canned = Image.new("RGB", (8, 8), (255, 0, 0))
    deps = (bucket, FakeImagePipe(canned), None, FakeTorchModule())

    out = e2e_target.run(worker_mod, {"prompt": "a red square", "seed": 7}, deps)

    assert bucket.fetch(out["artifact"]["presigned_url"].rsplit("/", 1)[-1]) == _png_bytes(canned)


@pytest.mark.deployed_e2e
def test_e2e_flash_generate_returns_image_artifact_deployed(e2e_target, bucket):
    canned = Image.new("RGB", (8, 8), (255, 0, 0))
    deps = (bucket, FakeImagePipe(canned), None, FakeTorchModule())

    out = e2e_target.run(worker_mod, {"prompt": "a red square", "seed": 7}, deps)

    assert bucket.fetch(out["artifact"]["presigned_url"].rsplit("/", 1)[-1]) == _png_bytes(canned)


@pytest.mark.deployed_e2e
def test_e2e_flash_rejects_missing_prompt_deployed(e2e_target, bucket):
    canned = Image.new("RGB", (8, 8), (255, 0, 0))
    deps = (bucket, FakeImagePipe(canned), None, FakeTorchModule())

    with pytest.raises(Exception, match="prompt"):
        e2e_target.run(worker_mod, {}, deps)
