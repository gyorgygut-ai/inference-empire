import pytest

import workers.h3.worker_beam_tq_minimax_h3_ref2va as worker_mod
from workers.services.inference.tiny_video import load_tiny_video_pipe
from workers.services.write_video_audio.write_video_audio import write_video_audio


def _deps(bucket):
    return (bucket, load_tiny_video_pipe(), write_video_audio)


@pytest.mark.local_e2e
def test_e2e_beam_generate_returns_video_artifact(e2e_target, bucket):
    out = e2e_target.run_async(worker_mod, {"prompt": "clip"}, _deps(bucket))

    assert "artifact" in out
    key = out["artifact"]["presigned_url"].rsplit("/", 1)[-1]
    assert bucket.has(key)
    assert len(bucket.fetch(key)) > 0


@pytest.mark.deployed_e2e
def test_e2e_beam_generate_returns_video_artifact_deployed(e2e_target, bucket):
    canned = b"fake-video-bytes"

    out = e2e_target.run_async(worker_mod, {"prompt": "clip"}, _deps(canned, bucket))

    assert bucket.fetch(out["artifact"]["presigned_url"].rsplit("/", 1)[-1]) == canned


@pytest.mark.deployed_e2e
def test_e2e_beam_rejects_missing_prompt_deployed(e2e_target, bucket):
    canned = b"fake-video-bytes"

    with pytest.raises(Exception, match="prompt"):
        e2e_target.run_async(worker_mod, {}, _deps(canned, bucket))
