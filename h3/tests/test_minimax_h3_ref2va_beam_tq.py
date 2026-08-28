import importlib
import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Literal, Optional


class MiniMaxH3Ref2VAInput(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3Ref2VAInput")
    prompt: str
    ref_images: list[str] = Field(default=[], max_length=9)
    ref_videos: list[str] = Field(default=[], max_length=3)
    ref_video_audios: list[str] = Field(default=[], max_length=3)
    ref_audios: list[str] = Field(default=[], max_length=3)
    width: int = Field(default=1344)
    height: int = Field(default=768)
    length: int = Field(default=124)
    steps: int = Field(default=50)
    seed: Optional[int] = Field(default=None)


def test_input_valid():
    MiniMaxH3Ref2VAInput(prompt="a cinematic shot with <Picture 1>", ref_images=["abc"])


def test_input_prompt_required():
    with pytest.raises(ValidationError):
        MiniMaxH3Ref2VAInput(prompt=None)


def test_input_defaults():
    inp = MiniMaxH3Ref2VAInput(prompt="test")
    assert inp.ref_images == []
    assert inp.ref_videos == []
    assert inp.ref_audios == []
    assert inp.width == 1344
    assert inp.height == 768


def test_output_valid():
    from tests.e2e_local.conftest import assert_artifact_nonempty

    artifact = {"url": "https://r2.example.com/file.mp4", "key": "file.mp4", "size": 100}
    assert_artifact_nonempty(artifact)


def test_worker_import():
    mod = importlib.import_module("worker_beam_tq_minimax_h3_ref2va")
    assert hasattr(mod, "MiniMaxH3Ref2VAInput")
    assert hasattr(mod, "MiniMaxH3Ref2VAOutput")
