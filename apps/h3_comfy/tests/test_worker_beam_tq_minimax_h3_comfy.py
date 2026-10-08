from types import SimpleNamespace

import pytest
from pydantic import ValidationError

import apps.h3_comfy.worker_beam_tq_minimax_h3_comfy as worker_mod
from packages.h3_comfy.shared import (
    MiniMaxH3ComfyInput,
    MiniMaxH3ComfyOutput,
    do_inference,
)


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
    monkeypatch.setattr(worker_mod.requests, "post", lambda *_a, **_k: _Resp({"prompt_id": "pid1"}))

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
    monkeypatch.setattr(worker_mod, "R2Artifacts", lambda: bucket)
    storage, url = worker_mod.load_dependencies()
    assert storage is bucket
    assert url == "http://fake-comfy:8188"


def test_dispatch_returns_video_artifact(bucket, monkeypatch):
    canned = b"fake-video-bytes"
    _mock_comfy(monkeypatch, canned)
    ctx = SimpleNamespace(on_start_value=(bucket, "http://fake-comfy:8188"))
    out = worker_mod.dispatch.local(ctx, prompt="clip")
    assert bucket.fetch(_key_from(out["artifact"]["presigned_url"])) == canned


def test_workflow_scheduler_simple_and_steps():
    from packages.h3_comfy.shared import build_workflow

    req = MiniMaxH3ComfyInput(prompt="clip")
    wf = build_workflow(req)
    assert wf["sigmas"]["inputs"]["scheduler"] == "simple"
    assert wf["sigmas"]["inputs"]["steps"] == 20


def test_ensure_comfy_models_calls_snapshot_download_when_missing(monkeypatch):
    from pathlib import Path

    import apps.h3_comfy.worker_beam_tq_minimax_h3_comfy as worker_mod
    monkeypatch.setattr(worker_mod.os, "makedirs", lambda *_a, **_k: None)
    called = {}
    def fake_snapshot(repo_id, local_dir, local_dir_use_symlinks=False, allow_patterns=None):
        called["repo"] = repo_id
        called["dir"] = local_dir
        called["patterns"] = allow_patterns
        called["use_symlinks"] = local_dir_use_symlinks
    monkeypatch.setattr(worker_mod, "snapshot_download", fake_snapshot)
    monkeypatch.setattr(Path, "exists", lambda _self: True)
    monkeypatch.setattr(worker_mod.shutil, "copy2", lambda *_a, **_k: None)
    worker_mod._ensure_comfy_models()
    assert called.get("repo") == "Comfy-Org/MiniMax-H3"
    assert str(called.get("dir")).endswith("/hf-cache/diffsynth")
    assert sorted(p.split("/")[-1] for p in called.get("patterns")) == sorted(worker_mod.COMFY_MODELS)


def test_workflow_seed_default_and_set():
    from packages.h3_comfy.shared import build_workflow

    assert build_workflow(MiniMaxH3ComfyInput(prompt="clip"))["noise"]["inputs"]["noise_seed"] == 42
    assert build_workflow(MiniMaxH3ComfyInput(prompt="clip", seed=7))["noise"]["inputs"]["noise_seed"] == 7


def test_first_last_frame_workflow_and_images():
    from packages.h3_comfy.shared import build_images, build_workflow

    _img = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    req = MiniMaxH3ComfyInput(prompt="clip", first_frame=_img, last_frame=_img)
    wf = build_workflow(req)
    assert "load_first" in wf
    assert "load_last" in wf
    assert len(build_images(req)) == 2


def test_output_uploaded_to_bucket(bucket, monkeypatch):
    canned = b"fake-video-bytes"
    _mock_comfy(monkeypatch, canned)
    req = MiniMaxH3ComfyInput(prompt="clip")
    out = do_inference("http://fake-comfy:8188", bucket, req)
    assert bucket.fetch(_key_from(out.artifact.presigned_url)) == canned
