import importlib

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Optional


class Input(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3Fl2VAInput")
    prompt: str
    width: int = Field(default=1344)
    height: int = Field(default=768)
    length: int = Field(default=124)
    steps: int = Field(default=50)
    seed: Optional[int] = Field(default=None)
    first_frame: Optional[str] = Field(default=None)
    last_frame: Optional[str] = Field(default=None)


class Output(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3Fl2VAOutput")

    class Artifact(BaseModel):
        model_config = ConfigDict(title="Artifact")
        url: str
        key: str
        size: int

    artifact: Artifact


def test_module_import():
    importlib.import_module("worker_flash_cls_minimax_h3_fl2va")


def test_input_valid():
    Input(prompt="a cinematic shot", first_frame="abc")


def test_input_prompt_required():
    with pytest.raises(ValidationError):
        Input(prompt=None)


def test_output_valid():
    Output(
        artifact={"url": "https://r2.example.com/file.mp4", "key": "file.mp4", "size": 100},
    )
