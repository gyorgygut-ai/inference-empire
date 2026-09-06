from types import SimpleNamespace

import numpy as np
import pytest

import workers.h3.worker_modal_cls_minimax_h3_ref2va as worker_mod
from workers.services.inference.video_pipe_fake import FakeVideoPipe
from workers.services.write_video_audio.write_video_audio_fake import (
    FakeWriteVideoAudio,
)


def _deps(canned):
    pipe = FakeVideoPipe(np.zeros((1, 4, 8, 8), dtype=np.uint8), None)
    pipe.audio_vae = SimpleNamespace(sample_rate=24000)
    return (pipe, FakeWriteVideoAudio(canned))


@pytest.mark.local_e2e
def test_e2e_modal_generate_serves_canned_video(e2e_target, bucket):
    canned = b"fake-video-bytes"

    out = e2e_target.run_async(worker_mod, {"prompt": "clip"}, _deps(canned), bucket)

    assert bucket.fetch(out["artifact"]["presigned_url"].rsplit("/", 1)[-1]) == canned


@pytest.mark.deployed_e2e
def test_e2e_modal_generate_serves_canned_video_deployed(e2e_target, bucket):
    canned = b"fake-video-bytes"

    out = e2e_target.run_async(worker_mod, {"prompt": "clip"}, _deps(canned), bucket)

    assert bucket.fetch(out["artifact"]["presigned_url"].rsplit("/", 1)[-1]) == canned
