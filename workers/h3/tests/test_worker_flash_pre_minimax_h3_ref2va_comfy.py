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


def test_generate_serves_canned_video(bucket):
    canned = b"fake-video-bytes"

    out = worker_mod.generate(bucket, _Endpoint(canned), prompt="clip")

    assert bucket.fetch(out["artifact"]["presigned_url"].rsplit("/", 1)[-1]) == canned
