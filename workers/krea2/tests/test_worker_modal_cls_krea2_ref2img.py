from workers.krea2.testing import KREA2_MODAL_CLS as SPEC


def test_generate_rejects_invalid_input(platform, runner, storage):
    worker = platform.create_worker(storage=storage)
    try:
        runner.run(worker, prompt=None)
        assert False, "Should reject"
    except Exception as e:
        assert "prompt" in str(e)


def test_generate_returns_output_contract_on_inference_failure(platform, runner, storage):
    worker = platform.create_worker(storage=storage)
    try:
        runner.run(worker, prompt="invalid_input_that_causes_failure")
        assert False, "Should raise"
    except RuntimeError as e:
        assert "inference" in str(e)


def test_generate_returns_output_contract_on_inference_success(platform, runner, storage):
    result = runner.run(platform.create_worker(storage=storage), prompt="a cat")
    assert "artifact" in result
    assert "presigned_url" in result["artifact"]
    assert result["artifact"]["presigned_url"].startswith("https://")


def test_generate_artifact_was_uploaded_to_storage(platform, runner, storage):
    result = runner.run(platform.create_worker(storage=storage), prompt="a cat")
    presigned_url = result["artifact"]["presigned_url"]
    artifact_key = presigned_url.split("/")[-1].split("?")[0]
    assert storage.has(artifact_key), f"Artifact {artifact_key} not found"
    body = storage.fetch(artifact_key)
    assert len(body) > 0
