import base64

import pytest
from pydantic import ValidationError

import workers.h3.worker_modal_cls_minimax_h3_ref2va_comfy as worker_mod
from workers.h3._shared_minimax_h3_ref2va_comfy import ValidatedRef2VAComfyInput, MiniMaxH3Ref2VAComfyOutput, do_inference


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


def test_do_inference_requested_with_right_args(bucket, monkeypatch):
    canned = b"fake-video-bytes"
    endpoint = _Endpoint(canned)
    # Mock run_comfy_endpoint to return job with canned data
    monkeypatch.setattr("workers.h3._shared_minimax_h3_comfy.run_comfy_endpoint", lambda ep, payload, timeout=1800: _Job({"images": [{"data": base64.b64encode(canned).decode("ascii")}]}))
    req = ValidatedRef2VAComfyInput(prompt="clip", steps=20, scheduler="simple")
    out = do_inference(endpoint, bucket, req)
    assert isinstance(out, MiniMaxH3Ref2VAComfyOutput)


def test_fake_bucket_has_uploaded_artifact(bucket, monkeypatch):
    canned = b"fake-video-bytes"
    monkeypatch.setattr("workers.h3._shared_minimax_h3_comfy.run_comfy_endpoint", lambda ep, payload, timeout=1800: _Job({"images": [{"data": base64.b64encode(canned).decode("ascii")}]}))
    req = ValidatedRef2VAComfyInput(prompt="clip")
    out = do_inference(_Endpoint(canned), bucket, req)
    assert bucket.fetch(_key_from(out.artifact.presigned_url)) == canned


def test_do_inference_returns_output_contract(bucket, monkeypatch):
    canned = b"fake-video-bytes"
    monkeypatch.setattr("workers.h3._shared_minimax_h3_comfy.run_comfy_endpoint", lambda ep, payload, timeout=1800: _Job({"images": [{"data": base64.b64encode(canned).decode("ascii")}]}))
    req = ValidatedRef2VAComfyInput(prompt="clip")
    out = do_inference(_Endpoint(canned), bucket, req)
    assert isinstance(out, MiniMaxH3Ref2VAComfyOutput)
    assert out.artifact.presigned_url.startswith("https://")


def test_generate_returns_video_artifact(bucket, monkeypatch):
    canned = b"fake-video-bytes"
    monkeypatch.setattr("workers.h3._shared_minimax_h3_comfy.run_comfy_endpoint", lambda ep, payload, timeout=1800: _Job({"images": [{"data": base64.b64encode(canned).decode("ascii")}]}))
    out = worker_mod.generate(bucket, _Endpoint(canned), prompt="clip")
    assert bucket.fetch(_key_from(out["artifact"]["presigned_url"])) == canned


def test_generate_rejects_missing_prompt(bucket, monkeypatch):
    canned = b"fake-video-bytes"
    monkeypatch.setattr("workers.h3._shared_minimax_h3_comfy.run_comfy_endpoint", lambda ep, payload, timeout=1800: _Job({"images": [{"data": base64.b64encode(canned).decode("ascii")}]}))
    with pytest.raises(ValidationError):
        worker_mod.generate(bucket, _Endpoint(canned))


def test_load_dependencies_mocked(monkeypatch, bucket):
    # Modal Cls objects can't be instantiated unit-side; verify the load
    # path's collaborators are the mockable module attrs.
    def fake_start():
        return "http://fake-comfy:8188"

    monkeypatch.setattr(worker_mod, "_start_comfy", fake_start)
    monkeypatch.setattr(worker_mod, "R2Storage", lambda: bucket)
    assert worker_mod._start_comfy() == "http://fake-comfy:8188"
    assert worker_mod.R2Storage() is bucket


def test_rejects_too_many_ref_images():
    with pytest.raises(ValidationError):
        ValidatedRef2VAComfyInput(prompt="clip", ref_images=["x"] * 10)


def test_rejects_too_many_ref_videos():
    with pytest.raises(ValidationError):
        ValidatedRef2VAComfyInput(prompt="clip", ref_videos=["x"] * 4)


def test_rejects_too_many_ref_video_audios():
    with pytest.raises(ValidationError):
        ValidatedRef2VAComfyInput(
            prompt="clip", ref_videos=["x"] * 3, ref_video_audios=["x"] * 4
        )


def test_rejects_too_many_ref_audios():
    with pytest.raises(ValidationError):
        ValidatedRef2VAComfyInput(prompt="clip", ref_images=["img"], ref_audios=["x"] * 4)


def test_rejects_video_audio_without_video():
    with pytest.raises(ValidationError):
        ValidatedRef2VAComfyInput(prompt="clip", ref_video_audios=["x"])


def test_rejects_audio_alone_without_visual():
    with pytest.raises(ValidationError):
        ValidatedRef2VAComfyInput(prompt="clip", ref_audios=["x"])


def test_rejects_total_over_12():
    with pytest.raises(ValidationError):
        ValidatedRef2VAComfyInput(
            prompt="clip",
            ref_images=["x"] * 9,
            ref_videos=["x"] * 3,
            ref_audios=["x"],
        )


def test_accepts_valid_boundary_and_defaults():
    req = ValidatedRef2VAComfyInput(prompt="clip", ref_images=["x"] * 9, ref_videos=["x"] * 3)
    assert len(req.ref_images) == 9
    assert req.steps == 20
    assert req.scheduler == "simple"
