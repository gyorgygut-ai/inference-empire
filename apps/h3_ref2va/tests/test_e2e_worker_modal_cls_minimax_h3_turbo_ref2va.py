import modal

from apps.h3_ref2va._shared_minimax_h3_turbo_ref2va import Artifact, MiniMaxH3TurboRef2vaOutput


def test_good_input_returns_contract_and_artifact(artifact_exists):
    Cls = modal.Cls.from_name("minimax-h3-turbo-ref2va-worker", "MiniMaxH3TurboRef2vaWorker")
    call = Cls().generate.spawn(prompt="a cat walking in a garden", seed=7)
    out = call.get(timeout=3600)
    url = out["artifact"]["presigned_url"]
    assert out == MiniMaxH3TurboRef2vaOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert artifact_exists(url, timeout=120)
