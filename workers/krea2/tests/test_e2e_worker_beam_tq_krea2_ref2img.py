from workers.artifact_check import artifact_exists
from workers.krea2._shared_krea2_ref2img import Artifact, Krea2Ref2ImgOutput

GOOD = {"prompt": "a red square", "seed": 7}


def test_good_input_returns_contract_and_artifact():
    import workers.krea2.worker_beam_tq_krea2_ref2img as worker_mod

    task = worker_mod.dispatch.put(**GOOD)
    out = task.result(wait=True)
    assert out is not None, "beam task returned None - check beam logs"

    url = out["artifact"]["presigned_url"]
    assert out == Krea2Ref2ImgOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert artifact_exists(url)
