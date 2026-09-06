import pytest

import workers.h3.worker_beam_tq_minimax_h3_ref2va_comfy as worker_mod


class _Resp:
    def __init__(self, payload=None, content=None):
        self._payload = payload
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _patch_requests(monkeypatch, canned):
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
    monkeypatch.setattr(
        worker_mod.requests, "post", lambda *a, **k: _Resp({"prompt_id": "pid1"})
    )

    def _get(url, **kwargs):
        if "history" in url:
            return _Resp(history)
        return _Resp(content=canned)

    monkeypatch.setattr(worker_mod.requests, "get", _get)


@pytest.mark.local_e2e
def test_e2e_beam_generate_returns_video_artifact(e2e_target, bucket, monkeypatch):
    canned = b"fake-video-bytes"
    _patch_requests(monkeypatch, canned)

    out = e2e_target.run_async(
        worker_mod, {"prompt": "clip"}, (bucket, "http://fake-comfy:8188")
    )

    assert "artifact" in out
    key = out["artifact"]["presigned_url"].rsplit("/", 1)[-1]
    assert bucket.has(key)
    assert len(bucket.fetch(key)) > 0


