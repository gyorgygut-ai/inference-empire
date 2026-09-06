import pytest

import workers.krea2.worker_modal_cls_krea2_ref2img as worker_mod
from workers.services.inference.tiny_image import load_tiny_image_pipe
from workers.services.torch_module.torch_module_fake import FakeTorchModule


@pytest.mark.local_e2e
def test_e2e_modal_generate_returns_image_artifact(e2e_target, bucket):
    deps = (bucket, load_tiny_image_pipe(), None, FakeTorchModule())

    out = e2e_target.run_async(
        worker_mod, {"prompt": "a red square", "seed": 7}, deps
    )

    assert "artifact" in out
    key = out["artifact"]["presigned_url"].rsplit("/", 1)[-1]
    assert bucket.has(key)
    assert len(bucket.fetch(key)) > 0


