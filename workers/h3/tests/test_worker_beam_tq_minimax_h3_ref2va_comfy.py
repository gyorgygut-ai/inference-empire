import base64
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

import workers.h3.worker_beam_tq_minimax_h3_ref2va_comfy as worker_mod
from workers.h3._shared_minimax_h3_ref2va_comfy import ValidatedRef2VAComfyInput, MiniMaxH3Ref2VAComfyOutput, do_inference


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
    req = ValidatedRef2VAComfyInput(prompt="clip", steps=20, scheduler="simple")
    out = do_inference("http://fake-comfy:8188", bucket, req)
    assert isinstance(out, MiniMaxH3Ref2VAComfyOutput)
    assert out.video == base64.b64encode(canned).decode("ascii")


def test_fake_bucket_has_uploaded_artifact(bucket, monkeypatch):
    canned = b"fake-video-bytes"
    _mock_comfy(monkeypatch, canned)
    req = ValidatedRef2VAComfyInput(prompt="clip")
    out = do_inference("http://fake-comfy:8188", bucket, req)
    assert bucket.fetch(_key_from(out.artifact.presigned_url)) == canned


def test_do_inference_returns_output_contract(bucket, monkeypatch):
    canned = b"fake-video-bytes"
    _mock_comfy(monkeypatch, canned)
    req = ValidatedRef2VAComfyInput(prompt="clip")
    out = do_inference("http://fake-comfy:8188", bucket, req)
    assert isinstance(out, MiniMaxH3Ref2VAComfyOutput)
    assert out.artifact.presigned_url.startswith("https://")


def test_generate_returns_video_artifact(bucket, monkeypatch):
    canned = b"fake-video-bytes"
    _mock_comfy(monkeypatch, canned)
    out = worker_mod.generate(bucket, "http://fake-comfy:8188", prompt="clip")
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
    storage, url = worker_mod.load_dependencies()
    assert storage is not None
    assert url == "http://fake-comfy:8188"


def test_dispatch_returns_video_artifact(bucket, monkeypatch):
    canned = b"fake-video-bytes"
    _mock_comfy(monkeypatch, canned)
    ctx = SimpleNamespace(on_start_value=(bucket, "http://fake-comfy:8188"))
    out = worker_mod.dispatch.local(ctx, prompt="clip")
    assert bucket.fetch(_key_from(out["artifact"]["presigned_url"])) == canned
