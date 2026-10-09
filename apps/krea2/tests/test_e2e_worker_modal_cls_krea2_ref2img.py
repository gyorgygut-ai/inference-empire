import os

from apps.krea2.shared.worker_krea2 import (
    Artifact,
    Krea2Ref2ImgInput,
    Krea2Ref2ImgOutput,
    do_inference,
    load_dependencies,
)


def test_good_input_returns_contract_and_artifact(artifact_exists):
    storage, pipe, runtime_dir, torch_module = load_dependencies()
    req = Krea2Ref2ImgInput(prompt="a red square", seed=7)
    out = do_inference(pipe, runtime_dir, torch_module, storage, req)
    url = out.artifact.presigned_url
    assert out == Krea2Ref2ImgOutput(artifact=Artifact(presigned_url=url))
    assert artifact_exists(url)


if __name__ == "__main__":
    os.environ.setdefault("HF_TOKEN", "")
    os.environ.setdefault("R2_ACCESS_KEY", "")
    os.environ.setdefault("R2_SECRET_KEY", "")
    os.environ.setdefault("R2_ENDPOINT", "")
    from apps.conftest import _artifact_exists
    test_good_input_returns_contract_and_artifact(_artifact_exists)
    print("E2E PASSED")
