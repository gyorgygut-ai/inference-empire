from packages.flux2.shared import Artifact, Flux2Klein9bOutput


def test_good_input_returns_contract_and_artifact(artifact_exists):
    import apps.flux2.worker_beam_tq_flux2_klein9b as worker_mod

    task = worker_mod.dispatch.put(prompt="a red square", seed=7)
    out = task.result(wait=True)
    assert out is not None, "beam task returned None - check beam logs"

    url = out["artifact"]["presigned_url"]
    assert out == Flux2Klein9bOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert artifact_exists(url)
