import base64

import pytest

import workers.h3.worker_flash_cls_minimax_h3_comfy as worker_mod


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


@pytest.mark.local_e2e
def test_e2e_flash_generate_returns_video_artifact(e2e_target, bucket):
    canned = b"fake-video-bytes"

    out = e2e_target.run(worker_mod, {"prompt": "clip"}, (bucket, _Endpoint(canned)))

    assert "artifact" in out
    key = out["artifact"]["presigned_url"].rsplit("/", 1)[-1]
    assert bucket.has(key)
    assert len(bucket.fetch(key)) > 0


