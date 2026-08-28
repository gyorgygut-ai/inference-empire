import pytest
from pydantic import ValidationError

from tests.conftest import _load_worker

_cls = _load_worker("worker_modal_cls_minimax_h3_ref2va", "MiniMaxH3Ref2VAInput")
ValidatedInput = _load_worker("worker_modal_cls_minimax_h3_ref2va", "ValidatedRef2VAInput")
Output = _load_worker("worker_modal_cls_minimax_h3_ref2va", "MiniMaxH3Ref2VAOutput")


def test_input_valid():
    _cls(prompt="a cinematic shot with <Picture 1>", ref_images=["abc"])


def test_input_prompt_required():
    with pytest.raises(ValidationError):
        _cls(prompt=None)


def test_validated_ref_images_limit():
    with pytest.raises(ValidationError):
        ValidatedInput(prompt="test", ref_images=["img"] * 10)


def test_validated_ref_videos_limit():
    with pytest.raises(ValidationError):
        ValidatedInput(prompt="test", ref_videos=["vid"] * 4)


def test_output_valid():
    Output(artifact={"url": "https://r2.example.com/file.mp4", "key": "file.mp4", "size": 100})
