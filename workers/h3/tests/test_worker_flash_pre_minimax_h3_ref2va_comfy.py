import base64

import workers.h3.worker_flash_pre_minimax_h3_ref2va_comfy as worker_mod


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


def test_generate_returns_video_artifact(bucket):
    canned = b"fake-video-bytes"

    out = worker_mod.generate(bucket, _Endpoint(canned), prompt="clip")

    assert bucket.fetch(out["artifact"]["presigned_url"].rsplit("/", 1)[-1]) == canned


def test_init_stores_storage_and_endpoint(monkeypatch, bucket):
    monkeypatch.setattr(worker_mod, "require_storage", lambda _s: bucket)
    monkeypatch.setattr(
        worker_mod, "load_dependencies", lambda: (_Endpoint(b"x"),)
    )

    # _class_type is the raw class; the decorator wraps it in a remote proxy.
    worker = worker_mod.MiniMaxH3Ref2VAComfyWorker()._class_type()

    assert worker.storage is bucket
    assert isinstance(worker.endpoint, _Endpoint)
