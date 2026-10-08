import modal

from packages.krea2.shared import Artifact, Krea2Ref2ImgOutput


def test_good_input_returns_contract_and_artifact(artifact_exists):
    Cls = modal.Cls.from_name("krea2-ref2img-worker", "Krea2Ref2ImgWorker")
    out = Cls().generate.remote(prompt="a red square", seed=7)
    url = out["artifact"]["presigned_url"]
    assert out == Krea2Ref2ImgOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert artifact_exists(url)
