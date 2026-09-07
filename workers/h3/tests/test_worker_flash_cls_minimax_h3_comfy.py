import base64

import pytest
from pydantic import ValidationError

import workers.h3.worker_flash_cls_minimax_h3_comfy as worker_mod
from workers.h3._shared_minimax_h3_comfy import MiniMaxH3ComfyInput, MiniMaxH3ComfyOutput, do_inference


class _Job:
    def __init__(self, output):
        self.error = None
        self.output = output


class _Endpoint:
    def __init__(self, canned):
        data = base64.b64encode(canned).decode("ascii")
        self._job = _Job({"images": [{"data": data}]})

    async def runsync(self, payload, timeout=None):
        return self._job


def _key_from(url):
    return url.rsplit("/", 1)[-1].split("?", 1)[0]


def test_do_inference_requested_with_right_args(bucket):
    canned = b"fake-video-bytes"
    endpoint = _Endpoint(canned)
    req = MiniMaxH3ComfyInput(prompt="clip", steps=20)
    out = do_inference(endpoint, bucket, req)
    assert isinstance(out, MiniMaxH3ComfyOutput)
    assert out.video == base64.b64encode(canned).decode("ascii")


def test_fake_bucket_has_uploaded_artifact(bucket):
    canned = b"fake-video-bytes"
    endpoint = _Endpoint(canned)
    req = MiniMaxH3ComfyInput(prompt="clip")
    out = do_inference(endpoint, bucket, req)
    assert bucket.fetch(_key_from(out.artifact.presigned_url)) == canned


def test_do_inference_returns_output_contract(bucket):
    canned = b"fake-video-bytes"
    endpoint = _Endpoint(canned)
    req = MiniMaxH3ComfyInput(prompt="clip")
    out = do_inference(endpoint, bucket, req)
    assert isinstance(out, MiniMaxH3ComfyOutput)
    assert out.artifact.presigned_url.startswith("https://")
    assert out.video


def test_generate_returns_video_artifact(bucket):
    canned = b"fake-video-bytes"
    out = worker_mod.generate(bucket, _Endpoint(canned), prompt="clip")
    assert bucket.fetch(out["artifact"]["presigned_url"].rsplit("/", 1)[-1]) == canned


def test_generate_rejects_missing_prompt(bucket):
    with pytest.raises(ValidationError):
        worker_mod.generate(bucket, _Endpoint(b"x"))


def test_load_dependencies_mocked(monkeypatch, bucket):
    canned = b"fake-video-bytes"
    fake_endpoint = _Endpoint(canned)

    def fake_load():
        return (fake_endpoint,)

    monkeypatch.setattr(worker_mod, "load_dependencies", fake_load)
    (ep,) = worker_mod.load_dependencies()
    assert ep is fake_endpoint


def test_workflow_scheduler_simple_and_steps():
    from workers.h3._shared_minimax_h3_comfy import build_workflow

    req = MiniMaxH3ComfyInput(prompt="clip")
    wf = build_workflow(req)
    assert wf["sigmas"]["inputs"]["scheduler"] == "simple"
    assert wf["sigmas"]["inputs"]["steps"] == 20


def test_workflow_seed_default_and_set():
    from workers.h3._shared_minimax_h3_comfy import build_workflow

    assert build_workflow(MiniMaxH3ComfyInput(prompt="clip"))["noise"]["inputs"]["noise_seed"] == 42
    assert build_workflow(MiniMaxH3ComfyInput(prompt="clip", seed=7))["noise"]["inputs"]["noise_seed"] == 7


def test_first_last_frame_workflow_and_images():
    from workers.h3._shared_minimax_h3_comfy import build_images, build_workflow

    req = MiniMaxH3ComfyInput(prompt="clip", first_frame="abc", last_frame="def")
    wf = build_workflow(req)
    assert "load_first" in wf
    assert "load_last" in wf
    assert len(build_images(req)) == 2
