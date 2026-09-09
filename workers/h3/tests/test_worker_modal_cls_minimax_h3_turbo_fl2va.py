from types import SimpleNamespace

import numpy as np
import pytest
from pydantic import ValidationError

import workers.h3.worker_modal_cls_minimax_h3_turbo_fl2va as worker_mod
from workers.h3._shared_minimax_h3_turbo_fl2va import MiniMaxH3TurboFl2vaInput, MiniMaxH3TurboFl2vaOutput, do_inference
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
    req = MiniMaxH3TurboFl2vaInput(prompt="clip", length=124, height=768, width=1344)
    do_inference(spy, FakeWriteVideoAudio(b"fake-video-bytes"), bucket, req)
    assert spy.kwargs["prompt"] == "clip"
    assert spy.kwargs["num_frames"] == 124
    assert spy.kwargs["num_inference_steps"] == 4
    assert spy.kwargs["flow_shift"] == 6.0
    assert spy.kwargs["audio_flow_shift"] == 3.0
    assert spy.kwargs["height"] == 768
    assert spy.kwargs["width"] == 1344


def test_fake_bucket_has_uploaded_artifact(bucket):
    canned = b"fake-video-bytes"
    out = do_inference(_pipe(), FakeWriteVideoAudio(canned), bucket, MiniMaxH3TurboFl2vaInput(prompt="clip"))
    assert bucket.fetch(_key_from(out.artifact.presigned_url)) == canned


def test_do_inference_returns_output_contract(bucket):
    canned = b"fake-video-bytes"
    out = do_inference(_pipe(), FakeWriteVideoAudio(canned), bucket, MiniMaxH3TurboFl2vaInput(prompt="clip"))
    assert isinstance(out, MiniMaxH3TurboFl2vaOutput)


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

    def fake_load():
        return bucket, fake_pipe, fake_write

    monkeypatch.setattr(worker_mod, "load_dependencies", fake_load)
    storage, pipe, write = worker_mod.load_dependencies()
    assert storage is bucket


_TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def test_seed_passthrough(bucket):
    spy = SpyPipe(np.zeros((1, 4, 8, 8), dtype=np.uint8), None)
    do_inference(
        spy, FakeWriteVideoAudio(b"x"), bucket, MiniMaxH3TurboFl2vaInput(prompt="clip", seed=7)
    )
    assert spy.kwargs["seed"] == 7


def test_seed_none_omitted(bucket):
    spy = SpyPipe(np.zeros((1, 4, 8, 8), dtype=np.uint8), None)
    do_inference(
        spy, FakeWriteVideoAudio(b"x"), bucket, MiniMaxH3TurboFl2vaInput(prompt="clip")
    )
    assert "seed" not in spy.kwargs


def test_first_last_frame_passthrough(bucket):
    spy = SpyPipe(np.zeros((1, 4, 8, 8), dtype=np.uint8), None)
    req = MiniMaxH3TurboFl2vaInput(
        prompt="clip", first_frame=_TINY_PNG_B64, last_frame=_TINY_PNG_B64
    )
    do_inference(spy, FakeWriteVideoAudio(b"x"), bucket, req)
    assert len(spy.kwargs["keyframes"]) == 2
    assert spy.kwargs["keyframe_indices"] == [0, -1]


def test_defaults_match_contract(bucket):
    req = MiniMaxH3TurboFl2vaInput(prompt="clip")
    assert req.width == 1344
    assert req.height == 768
    assert req.length == 124
    assert req.seed is None
    assert req.first_frame is None
    assert req.last_frame is None
