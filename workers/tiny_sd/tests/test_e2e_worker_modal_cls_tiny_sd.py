import modal


def test_modal_generate_returns_image_artifact():
    result = modal.Cls.from_name("tiny-sd-worker", "TinySDWorker").generate.remote(
        prompt="a red square", seed=7
    )
    assert "artifact" in result
    assert "presigned_url" in result["artifact"]
