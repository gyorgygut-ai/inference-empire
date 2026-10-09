import os

from apps.flux2.shared.worker_flux2 import (
    Artifact,
    Flux2Klein9bInput,
    Flux2Klein9bOutput,
    do_inference,
    load_dependencies,
)


def test_good_input_returns_contract_and_artifact(artifact_exists):
    storage, pipe, torch_module = load_dependencies()
    req = Flux2Klein9bInput(prompt="a red square", seed=7)
    out = do_inference(pipe, torch_module, storage, req)
    url = out.artifact.presigned_url
    assert out == Flux2Klein9bOutput(artifact=Artifact(presigned_url=url))
    assert artifact_exists(url)


if __name__ == "__main__":
    os.environ.setdefault("HF_TOKEN", "")
    os.environ.setdefault("R2_ACCESS_KEY", "")
    os.environ.setdefault("R2_SECRET_KEY", "")
    os.environ.setdefault("R2_ENDPOINT", "")
    from apps.conftest import _artifact_exists
    test_good_input_returns_contract_and_artifact(_artifact_exists)
    print("E2E PASSED")
