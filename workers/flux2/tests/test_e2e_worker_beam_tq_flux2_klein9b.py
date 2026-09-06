import pytest

import workers.flux2.worker_beam_tq_flux2_klein9b as worker_mod
from workers.services.inference.tiny_image import load_tiny_image_pipe
from workers.services.torch_module.torch_module_fake import FakeTorchModule


@pytest.mark.local_e2e
def test_e2e_beam_generate_returns_image_artifact(e2e_target, bucket):
    deps = (bucket, load_tiny_image_pipe(), FakeTorchModule())

    out = e2e_target.run_async(
        worker_mod, {"prompt": "a red square", "seed": 7}, deps
    )

    assert "artifact" in out
    key = out["artifact"]["presigned_url"].rsplit("/", 1)[-1]
    assert bucket.has(key)
    assert len(bucket.fetch(key)) > 0


@pytest.mark.deployed_e2e
def test_e2e_beam_generate_returns_image_artifact_deployed(e2e_target, bucket):
    canned = Image.new("RGB", (8, 8), (255, 0, 0))
    deps = (bucket, FakeImagePipe(canned), FakeTorchModule())

    out = e2e_target.run_async(
        worker_mod, {"prompt": "a red square", "seed": 7}, deps
    )

    assert bucket.fetch(out["artifact"]["presigned_url"].rsplit("/", 1)[-1]) == _png_bytes(canned)


@pytest.mark.deployed_e2e
def test_e2e_beam_rejects_missing_prompt_deployed(e2e_target, bucket):
    canned = Image.new("RGB", (8, 8), (255, 0, 0))
    deps = (bucket, FakeImagePipe(canned), FakeTorchModule())

    with pytest.raises(Exception, match="prompt"):
        e2e_target.run_async(worker_mod, {}, deps)
