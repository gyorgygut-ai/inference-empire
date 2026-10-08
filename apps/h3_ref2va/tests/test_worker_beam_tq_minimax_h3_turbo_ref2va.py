from types import SimpleNamespace

import numpy as np
import pytest
from pydantic import ValidationError

import apps.h3_ref2va.worker_beam_tq_minimax_h3_ref2va as worker_mod
from apps.h3_ref2va.fakes.video_pipe_fake import FakeVideoPipe
from apps.h3_ref2va.fakes.write_video_audio_fake import FakeWriteVideoAudio
from packages.h3_ref2va.shared import (
    MiniMaxH3TurboRef2vaOutput,
    ValidatedRef2VAInput,
    do_inference,
)

# Real (tiny) payloads: validators reject junk strings, so count tests use these.
_IMG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
_VID = (
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="
)


def _pipe():
    pipe = FakeVideoPipe(np.zeros((1, 4, 8, 8), dtype=np.uint8), None)
    pipe.audio_vae = SimpleNamespace(sample_rate=24000)
    return pipe


class SpyPipe(FakeVideoPipe):
    def __init__(self, frames, audio):
        super().__init__(frames, audio)
        self.kwargs: dict = {}
        self.audio_vae = SimpleNamespace(sample_rate=24000)

    def __call__(self, **kwargs):
        self.kwargs = kwargs
        return super().__call__(**kwargs)


def _key_from(url):
    return url.rsplit("/", 1)[-1].split("?", 1)[0]


def test_do_inference_requested_with_right_args(bucket):
    spy = SpyPipe(np.zeros((1, 4, 8, 8), dtype=np.uint8), None)
    req = ValidatedRef2VAInput(prompt="clip")
    do_inference(spy, FakeWriteVideoAudio(b"fake-video-bytes"), bucket, req)
    assert spy.kwargs["num_inference_steps"] == 4
    assert spy.kwargs["flow_shift"] == 12.0
    assert spy.kwargs["audio_flow_shift"] == 3.0


def test_fake_bucket_has_uploaded_artifact(bucket):
    canned = b"fake-video-bytes"
    out = do_inference(_pipe(), FakeWriteVideoAudio(canned), bucket, ValidatedRef2VAInput(prompt="clip"))
    assert bucket.fetch(_key_from(out.artifact.presigned_url)) == canned


def test_do_inference_returns_output_contract(bucket):
    canned = b"fake-video-bytes"
    out = do_inference(_pipe(), FakeWriteVideoAudio(canned), bucket, ValidatedRef2VAInput(prompt="clip"))
    assert isinstance(out, MiniMaxH3TurboRef2vaOutput)


def test_generate_returns_video_artifact(bucket):
    canned = b"fake-video-bytes"
    out = worker_mod.generate(bucket, _pipe(), FakeWriteVideoAudio(canned), prompt="clip")
    assert bucket.fetch(_key_from(out["artifact"]["presigned_url"])) == canned


def test_generate_rejects_missing_prompt(bucket):
    with pytest.raises(ValidationError):
        worker_mod.generate(bucket, _pipe(), FakeWriteVideoAudio(b"x"))


def test_rejects_too_many_ref_images():
    with pytest.raises(ValidationError):
        ValidatedRef2VAInput(prompt="clip", ref_images=[_IMG] * 10)


def test_rejects_too_many_ref_videos():
    with pytest.raises(ValidationError):
        ValidatedRef2VAInput(prompt="clip", ref_videos=[_VID] * 4)


def test_rejects_too_many_ref_video_audios():
    with pytest.raises(ValidationError):
        ValidatedRef2VAInput(
            prompt="clip", ref_videos=[_VID] * 3, ref_video_audios=[_VID] * 4
        )


def test_rejects_too_many_ref_audios():
    with pytest.raises(ValidationError):
        ValidatedRef2VAInput(prompt="clip", ref_images=[_IMG], ref_audios=[_VID] * 4)


def test_rejects_video_audio_without_video():
    with pytest.raises(ValidationError):
        ValidatedRef2VAInput(prompt="clip", ref_video_audios=[_VID])


def test_rejects_audio_alone_without_visual():
    with pytest.raises(ValidationError):
        ValidatedRef2VAInput(prompt="clip", ref_audios=[_VID])


def test_rejects_total_over_12():
    with pytest.raises(ValidationError):
        ValidatedRef2VAInput(
            prompt="clip",
            ref_images=[_IMG] * 9,
            ref_videos=[_VID] * 3,
            ref_audios=[_VID],
        )


def test_accepts_valid_boundary():
    req = ValidatedRef2VAInput(prompt="clip", ref_images=[_IMG] * 9, ref_videos=[_VID] * 3)
    assert len(req.ref_images) == 9
