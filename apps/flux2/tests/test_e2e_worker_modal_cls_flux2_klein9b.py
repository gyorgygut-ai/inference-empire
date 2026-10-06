import modal

from apps._artifact_check import artifact_exists
from apps.flux2._shared_flux2_klein9b import Artifact, Flux2Klein9bOutput


def test_good_input_returns_contract_and_artifact():
    Cls = modal.Cls.from_name("flux2-klein9b-worker", "FluxKleinWorker")
    call = Cls().generate.spawn(prompt="a red square", seed=7)
    out = call.get(timeout=600)
    url = out["artifact"]["presigned_url"]
    assert out == Flux2Klein9bOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert artifact_exists(url)
