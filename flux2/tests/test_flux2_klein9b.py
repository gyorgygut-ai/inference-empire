import importlib

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Optional


class Input(BaseModel):
    model_config = ConfigDict(title="Flux2Klein9bInput")
    prompt: str
    width: int = Field(default=1344)
    height: int = Field(default=768)
    steps: int = Field(default=20)
    seed: Optional[int] = Field(default=None)


class Output(BaseModel):
    model_config = ConfigDict(title="Flux2Klein9bOutput")

    class Artifact(BaseModel):
        model_config = ConfigDict(title="Artifact")
        url: str
        key: str
        size: int

    artifact: Artifact


def test_module_import():
    importlib.import_module("worker_flash_cls_flux2_klein9b")


def test_input_valid():
    Input(prompt="a cat")


def test_input_prompt_required():
    with pytest.raises(ValidationError):
        Input(prompt=None)


def test_output_valid():
    Output(
        artifact={"url": "https://r2.example.com/file.png", "key": "file.png", "size": 100},
    )
