import os

from apps.h3_ref2va.shared.worker_h3_ref2va import (
    Artifact,
    MiniMaxH3TurboRef2vaInput,
    MiniMaxH3TurboRef2vaOutput,
    do_inference,
    load_dependencies,
)


def test_good_input_returns_contract_and_artifact(artifact_exists):
    storage, pipe, write_video_audio = load_dependencies()
    req = MiniMaxH3TurboRef2vaInput(prompt="a cat walking in a garden", seed=7)
    out = do_inference(pipe, write_video_audio, storage, req)
    url = out.artifact.presigned_url
    assert out == MiniMaxH3TurboRef2vaOutput(artifact=Artifact(presigned_url=url))
    assert artifact_exists(url, timeout=120)


if __name__ == "__main__":
    os.environ.setdefault("HF_TOKEN", "")
    os.environ.setdefault("R2_ACCESS_KEY", "")
    os.environ.setdefault("R2_SECRET_KEY", "")
    os.environ.setdefault("R2_ENDPOINT", "")
    from apps.conftest import _artifact_exists
    test_good_input_returns_contract_and_artifact(_artifact_exists)
    print("E2E PASSED")
