from types import SimpleNamespace

import numpy as np
import pytest
from pydantic import ValidationError

import workers.h3.worker_beam_tq_minimax_h3_ref2va as worker_mod
from workers.services.inference.video_pipe_fake import FakeVideoPipe
from workers.services.write_video_audio.write_video_audio_fake import (
    FakeWriteVideoAudio,
)


def _pipe():
    pipe = FakeVideoPipe(np.zeros((1, 4, 8, 8), dtype=np.uint8), None)
    pipe.audio_vae = SimpleNamespace(sample_rate=24000)
    return pipe


def test_generate_returns_video_artifact(bucket):
    canned = b"fake-video-bytes"

    out = worker_mod.generate(bucket, _pipe(), FakeWriteVideoAudio(canned), prompt="clip")

    assert bucket.fetch(out["artifact"]["presigned_url"].rsplit("/", 1)[-1]) == canned


def test_generate_rejects_missing_prompt(bucket):
    with pytest.raises(ValidationError):
        worker_mod.generate(bucket, _pipe(), FakeWriteVideoAudio(b"x"))


def test_dispatch_returns_video_artifact(monkeypatch, bucket):
    canned = b"fake-video-bytes"
    monkeypatch.setattr(worker_mod, "require_storage", lambda _s: bucket)
    ctx = SimpleNamespace(on_start_value=(_pipe(), FakeWriteVideoAudio(canned)))

    # .local runs the raw function; the decorator blocks direct calls.
    out = worker_mod.dispatch.local(ctx, prompt="clip")

    assert bucket.fetch(out["artifact"]["presigned_url"].rsplit("/", 1)[-1]) == canned
