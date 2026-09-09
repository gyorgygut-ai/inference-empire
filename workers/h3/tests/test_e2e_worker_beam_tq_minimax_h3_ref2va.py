from workers.artifact_check import artifact_exists
from workers.h3._shared_minimax_h3_ref2va import Artifact, MiniMaxH3Ref2VAOutput


def test_good_input_returns_contract_and_artifact():
    import workers.h3.worker_beam_tq_minimax_h3_ref2va as worker_mod

    task = worker_mod.dispatch.put(prompt="a cat walking in a garden", seed=7)
    out = task.result(wait=True)
    assert out is not None, "beam task returned None - check beam logs"

    url = out["artifact"]["presigned_url"]
    assert out == MiniMaxH3Ref2VAOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert artifact_exists(url, timeout=120)
