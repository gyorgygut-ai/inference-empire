import importlib

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Optional


class Input(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3Ref2VAInput")
    prompt: str
    ref_images: list[str] = Field(default=[], max_length=9)
    ref_audios: list[str] = Field(default=[], max_length=3)
    width: int = Field(default=1344)
    height: int = Field(default=768)
    length: int = Field(default=124)
    steps: int = Field(default=20)
    seed: Optional[int] = Field(default=None)
    scheduler: str = Field(default="simple")


class Output(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3Ref2VAOutput")

    class Artifact(BaseModel):
        model_config = ConfigDict(title="Artifact")
        url: str
        key: str
        size: int

    artifact: Artifact


def test_module_import():
    importlib.import_module("worker_flash_cls_minimax_h3_ref2va")


def test_input_valid():
    Input(prompt="a cinematic shot", ref_images=["abc"])


def test_input_prompt_required():
    with pytest.raises(ValidationError):
        Input(prompt=None)


def test_input_ref_images_limit():
    with pytest.raises(ValidationError):
        Input(prompt="test", ref_images=["img"] * 10)


def test_output_valid():
    Output(
        artifact={"url": "https://r2.example.com/file.mp4", "key": "file.mp4", "size": 100},
    )
