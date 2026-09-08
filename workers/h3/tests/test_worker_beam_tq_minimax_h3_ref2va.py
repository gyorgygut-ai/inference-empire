from types import SimpleNamespace

import numpy as np
import pytest
from pydantic import ValidationError

import workers.h3.worker_beam_tq_minimax_h3_ref2va as worker_mod
from workers.h3._shared_minimax_h3_ref2va import ValidatedRef2VAInput, MiniMaxH3Ref2VAOutput, do_inference
from workers.services.inference.video_pipe_fake import FakeVideoPipe
from workers.services.write_video_audio.write_video_audio_fake import FakeWriteVideoAudio


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
    req = ValidatedRef2VAInput(prompt="clip", length=124, steps=50)
    do_inference(spy, FakeWriteVideoAudio(b"fake-video-bytes"), bucket, req)
    assert spy.kwargs["prompt"] == "clip"
    assert spy.kwargs["num_frames"] == 124
    assert spy.kwargs["num_inference_steps"] == 50


def test_fake_bucket_has_uploaded_artifact(bucket):
    canned = b"fake-video-bytes"
    out = do_inference(_pipe(), FakeWriteVideoAudio(canned), bucket, ValidatedRef2VAInput(prompt="clip"))
    assert bucket.fetch(_key_from(out.artifact.presigned_url)) == canned


def test_do_inference_returns_output_contract(bucket):
    canned = b"fake-video-bytes"
    out = do_inference(_pipe(), FakeWriteVideoAudio(canned), bucket, ValidatedRef2VAInput(prompt="clip"))
    assert isinstance(out, MiniMaxH3Ref2VAOutput)


def test_generate_returns_video_artifact(bucket):
    canned = b"fake-video-bytes"
    out = worker_mod.generate(bucket, _pipe(), FakeWriteVideoAudio(canned), prompt="clip")
    assert bucket.fetch(_key_from(out["artifact"]["presigned_url"])) == canned


def test_generate_rejects_missing_prompt(bucket):
    with pytest.raises(ValidationError):
        worker_mod.generate(bucket, _pipe(), FakeWriteVideoAudio(b"x"))


def test_load_dependencies_mocked(monkeypatch, bucket):
    fake_pipe = _pipe()
    fake_write = FakeWriteVideoAudio(b"x")

    def fake_load(cache_dir=None):
        return bucket, fake_pipe, fake_write

    monkeypatch.setattr(worker_mod, "load_dependencies", fake_load)
    storage, pipe, write = worker_mod.load_deps()
    assert storage is bucket


def test_dispatch_returns_video_artifact(bucket):
    canned = b"fake-video-bytes"
    ctx = SimpleNamespace(on_start_value=(bucket, _pipe(), FakeWriteVideoAudio(canned)))
    out = worker_mod.dispatch.local(ctx, prompt="clip")
    assert bucket.fetch(_key_from(out["artifact"]["presigned_url"])) == canned


def test_rejects_too_many_ref_images():
    with pytest.raises(ValidationError):
        ValidatedRef2VAInput(prompt="clip", ref_images=["x"] * 10)


def test_rejects_too_many_ref_videos():
    with pytest.raises(ValidationError):
        ValidatedRef2VAInput(prompt="clip", ref_videos=["x"] * 4)


def test_rejects_too_many_ref_video_audios():
    with pytest.raises(ValidationError):
        ValidatedRef2VAInput(
            prompt="clip", ref_videos=["x"] * 3, ref_video_audios=["x"] * 4
        )


def test_rejects_too_many_ref_audios():
    with pytest.raises(ValidationError):
        ValidatedRef2VAInput(prompt="clip", ref_images=["img"], ref_audios=["x"] * 4)


def test_rejects_video_audio_without_video():
    with pytest.raises(ValidationError):
        ValidatedRef2VAInput(prompt="clip", ref_video_audios=["x"])


def test_rejects_audio_alone_without_visual():
    with pytest.raises(ValidationError):
        ValidatedRef2VAInput(prompt="clip", ref_audios=["x"])


def test_rejects_total_over_12():
    with pytest.raises(ValidationError):
        ValidatedRef2VAInput(
            prompt="clip",
            ref_images=["x"] * 9,
            ref_videos=["x"] * 3,
            ref_audios=["x"],
        )


def test_accepts_valid_boundary():
    req = ValidatedRef2VAInput(prompt="clip", ref_images=["x"] * 9, ref_videos=["x"] * 3)
    assert len(req.ref_images) == 9
    assert len(req.ref_videos) == 3
