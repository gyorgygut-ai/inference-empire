import importlib
import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Literal, Optional


class MiniMaxH3Fl2VAInput(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3Fl2VAInput")
    prompt: str
    width: int = Field(default=1344)
    height: int = Field(default=768)
    length: int = Field(default=124)
    steps: int = Field(default=50)
    seed: Optional[int] = Field(default=None)
    first_frame: Optional[str] = Field(default=None)
    last_frame: Optional[str] = Field(default=None)


def test_input_valid():
    MiniMaxH3Fl2VAInput(prompt="a cinematic shot of a cat")


def test_input_prompt_required():
    with pytest.raises(ValidationError):
        MiniMaxH3Fl2VAInput(prompt=None)


def test_input_defaults():
    inp = MiniMaxH3Fl2VAInput(prompt="test")
    assert inp.width == 1344
    assert inp.height == 768
    assert inp.length == 124
    assert inp.steps == 50
    assert inp.seed is None
    assert inp.first_frame is None
    assert inp.last_frame is None


def test_output_valid():
    from tests.e2e_local.conftest import assert_artifact_nonempty

    artifact = {"url": "https://r2.example.com/file.mp4", "key": "file.mp4", "size": 100}
    assert_artifact_nonempty(artifact)


def test_worker_import():
    mod = importlib.import_module("worker_beam_tq_minimax_h3_fl2va")
    assert hasattr(mod, "MiniMaxH3Fl2VAInput")
    assert hasattr(mod, "MiniMaxH3Fl2VAOutput")
