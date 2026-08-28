import pytest
from pydantic import ValidationError

from tests.conftest import _load_worker

_cls = _load_worker("worker_modal_cls_minimax_h3_fl2va", "MiniMaxH3Fl2VAInput")
Output = _load_worker("worker_modal_cls_minimax_h3_fl2va", "MiniMaxH3Fl2VAOutput")


def test_input_valid():
    _cls(prompt="a cinematic shot of a cat")


def test_input_prompt_required():
    with pytest.raises(ValidationError):
        _cls(prompt=None)


def test_input_defaults():
    inp = _cls(prompt="test")
    assert inp.width == 1344
    assert inp.height == 768
    assert inp.length == 124
    assert inp.steps == 50
    assert inp.seed is None
    assert inp.first_frame is None
    assert inp.last_frame is None


def test_output_valid():
    Output(artifact={"url": "https://r2.example.com/file.mp4", "key": "file.mp4", "size": 100})
