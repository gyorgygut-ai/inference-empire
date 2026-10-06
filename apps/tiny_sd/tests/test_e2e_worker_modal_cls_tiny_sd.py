import modal

from apps.tiny_sd._shared_tiny_sd import Artifact, TinySDOutput


def test_good_input_returns_contract_and_artifact(artifact_exists):
    Cls = modal.Cls.from_name("tiny-sd-worker", "TinySDWorker")
    out = Cls().generate.remote(prompt="a red square", seed=7)
    url = out["artifact"]["presigned_url"]
    assert out == TinySDOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert artifact_exists(url)
