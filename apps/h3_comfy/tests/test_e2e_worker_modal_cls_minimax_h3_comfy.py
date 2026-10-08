import modal

from packages.h3_comfy.shared import Artifact, MiniMaxH3ComfyOutput


def test_good_input_returns_contract_and_artifact(artifact_exists):
    Cls = modal.Cls.from_name("minimax-h3-comfy-worker", "MiniMaxH3ComfyWorker")
    call = Cls().generate.spawn(prompt="a cat walking in a garden", seed=7)
    out = call.get(timeout=3600)
    url = out["artifact"]["presigned_url"]
    assert out == MiniMaxH3ComfyOutput(artifact=Artifact(presigned_url=url)).model_dump()
    assert artifact_exists(url)
