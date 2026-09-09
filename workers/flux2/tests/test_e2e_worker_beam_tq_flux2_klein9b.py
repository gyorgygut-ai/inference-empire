from workers.artifact_check import artifact_exists
from workers.flux2._shared_flux2_klein9b import Artifact, Flux2Klein9bOutput

GOOD = {"prompt": "a red square", "seed": 7}


def test_good_input_returns_contract_and_artifact():
    import workers.flux2.worker_beam_tq_flux2_klein9b as worker_mod

    task = worker_mod.dispatch.put(**GOOD)
    out = task.result(wait=True)
    assert out is not None, "beam task returned None - check beam logs"

    url = out["artifact"]["presigned_url"]
    assert out == Flux2Klein9bOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert artifact_exists(url)
