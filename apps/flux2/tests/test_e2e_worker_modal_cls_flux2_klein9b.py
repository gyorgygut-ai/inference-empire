import modal

from packages.flux2.shared import Artifact, Flux2Klein9bOutput


def test_good_input_returns_contract_and_artifact(artifact_exists):
    Cls = modal.Cls.from_name("flux2-klein9b-worker", "FluxKleinWorker")
    call = Cls().generate.spawn(prompt="a red square", seed=7)
    out = call.get(timeout=600)
    url = out["artifact"]["presigned_url"]
    assert out == Flux2Klein9bOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert artifact_exists(url)
