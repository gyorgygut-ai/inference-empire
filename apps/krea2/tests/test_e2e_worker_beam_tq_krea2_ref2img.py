from packages.krea2.shared import Artifact, Krea2Ref2ImgOutput


def test_good_input_returns_contract_and_artifact(artifact_exists):
    import apps.krea2.worker_beam_tq_krea2_ref2img as worker_mod

    task = worker_mod.dispatch.put(prompt="a red square", seed=7)
    out = task.result(wait=True)
    assert out is not None, "beam task returned None - check beam logs"

    url = out["artifact"]["presigned_url"]
    assert out == Krea2Ref2ImgOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert artifact_exists(url)
