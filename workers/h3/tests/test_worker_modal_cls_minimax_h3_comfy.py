import base64

import pytest
from pydantic import ValidationError

import workers.h3.worker_modal_cls_minimax_h3_comfy as worker_mod
from workers.h3._shared_minimax_h3_comfy import MiniMaxH3ComfyInput, MiniMaxH3ComfyOutput, do_inference


class _Resp:
    def __init__(self, payload=None, content=None):
        self._payload = payload
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _key_from(url):
    return url.rsplit("/", 1)[-1].split("?", 1)[0]


def _mock_comfy(monkeypatch, canned):
    history = {
        "pid1": {
            "outputs": {
                "save": {
                    "videos": [
                        {"filename": "v.mp4", "subfolder": "", "type": "output"},
                    ],
                },
            },
        },
    }
    monkeypatch.setattr(worker_mod.requests, "post", lambda *a, **k: _Resp({"prompt_id": "pid1"}))

    def _get(url, **kwargs):
        if "history" in url:
            return _Resp(history)
        return _Resp(content=canned)

    monkeypatch.setattr(worker_mod.requests, "get", _get)


def test_do_inference_requested_with_right_args(bucket, monkeypatch):
    canned = b"fake-video-bytes"
    _mock_comfy(monkeypatch, canned)
    req = MiniMaxH3ComfyInput(prompt="clip", steps=20)
    out = do_inference("http://fake-comfy:8188", bucket, req)
    assert isinstance(out, MiniMaxH3ComfyOutput)
    assert bucket.fetch(_key_from(out.artifact.presigned_url)) == canned


def test_fake_bucket_has_uploaded_artifact(bucket, monkeypatch):
    canned = b"fake-video-bytes"
    _mock_comfy(monkeypatch, canned)
    req = MiniMaxH3ComfyInput(prompt="clip")
    out = do_inference("http://fake-comfy:8188", bucket, req)
    assert bucket.fetch(_key_from(out.artifact.presigned_url)) == canned


def test_do_inference_returns_output_contract(bucket, monkeypatch):
    canned = b"fake-video-bytes"
    _mock_comfy(monkeypatch, canned)
    req = MiniMaxH3ComfyInput(prompt="clip")
    out = do_inference("http://fake-comfy:8188", bucket, req)
    assert isinstance(out, MiniMaxH3ComfyOutput)
    assert out.artifact.presigned_url.startswith("https://")


def test_generate_returns_artifact(bucket, monkeypatch):
    canned = b"fake-video-bytes"
    _mock_comfy(monkeypatch, canned)
    out = worker_mod.generate(bucket, "http://fake-comfy:8188", prompt="clip")
    assert out["artifact"]["presigned_url"].startswith("https://")
    assert bucket.fetch(_key_from(out["artifact"]["presigned_url"])) == canned


def test_generate_rejects_missing_prompt(bucket, monkeypatch):
    canned = b"fake-video-bytes"
    _mock_comfy(monkeypatch, canned)
    with pytest.raises(ValidationError):
        worker_mod.generate(bucket, "http://fake-comfy:8188")


def test_load_dependencies_mocked(monkeypatch, bucket):
    def fake_start():
        return "http://fake-comfy:8188"

    monkeypatch.setattr(worker_mod, "_start_comfy", fake_start)
    monkeypatch.setattr(worker_mod, "R2Storage", lambda: bucket)
    assert worker_mod._start_comfy() == "http://fake-comfy:8188"
    assert worker_mod.R2Storage() is bucket


def test_workflow_scheduler_simple_and_steps():
    from workers.h3._shared_minimax_h3_comfy import build_workflow

    req = MiniMaxH3ComfyInput(prompt="clip")
    wf = build_workflow(req)
    assert wf["sigmas"]["inputs"]["scheduler"] == "simple"
    assert wf["sigmas"]["inputs"]["steps"] == 20


def test_first_last_frame_workflow_and_images():
    from workers.h3._shared_minimax_h3_comfy import build_images, build_workflow

    req = MiniMaxH3ComfyInput(prompt="clip", first_frame="abc", last_frame="def")
    wf = build_workflow(req)
    assert "load_first" in wf
    assert "load_last" in wf
    assert len(build_images(req)) == 2
