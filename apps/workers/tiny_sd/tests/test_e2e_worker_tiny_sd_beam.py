from shared.worker_tiny_sd import (
    Artifact,
    TinySDInput,
    TinySDOutput,
    do_inference,
    load_dependencies,
)


def test_good_input_returns_contract_and_artifact(artifact_exists):
    storage, pipe, torch_module = load_dependencies()
    req = TinySDInput(prompt="a red square", seed=7)
    out = do_inference(pipe, torch_module, storage, req)
    url = out.artifact.presigned_url
    assert out == TinySDOutput(artifact=Artifact(presigned_url=url))
    assert artifact_exists(url)
