import asyncio

import pytest

import workers.tiny_sd.worker_flash_cls_tiny_sd as worker_mod


@pytest.mark.skip(reason="flash dev not available")
def test_flash_generate_returns_image_artifact():
    result = asyncio.run(
        worker_mod.TinySDWorker().generate(prompt="a red square", seed=7)
    )
    assert "artifact" in result
    assert "presigned_url" in result["artifact"]
