from workers.artifact_check import artifact_exists
from workers.tiny_sd._shared_tiny_sd import Artifact, TinySDOutput


def test_good_input_returns_contract_and_artifact():
    import workers.tiny_sd.worker_beam_tq_tiny_sd as worker_mod

    task = worker_mod.dispatch.put(prompt="a red square", seed=7)
    out = task.result(wait=True)
    assert out is not None, "beam task returned None - check beam logs"

    url = out["artifact"]["presigned_url"]
    assert out == TinySDOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert artifact_exists(url)
