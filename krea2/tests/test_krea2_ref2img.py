import importlib

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Optional


class Input(BaseModel):
    model_config = ConfigDict(title="Krea2Ref2ImgInput")
    prompt: str
    reference_image: str
    width: int = Field(default=1024)
    height: int = Field(default=1024)
    steps: int = Field(default=20)
    seed: Optional[int] = Field(default=None)
    strength: float = Field(default=0.75)


class Output(BaseModel):
    model_config = ConfigDict(title="Krea2Ref2ImgOutput")

    class Artifact(BaseModel):
        model_config = ConfigDict(title="Artifact")
        url: str
        key: str
        size: int

    artifact: Artifact


def test_module_import():
    importlib.import_module("worker_flash_cls_krea2_ref2img")


def test_input_valid():
    Input(prompt="a person", reference_image="abc")


def test_input_prompt_required():
    with pytest.raises(ValidationError):
        Input(prompt=None, reference_image="abc")


def test_input_reference_image_required():
    with pytest.raises(ValidationError):
        Input(prompt="a person", reference_image=None)


def test_output_valid():
    Output(
        artifact={"url": "https://r2.example.com/file.png", "key": "file.png", "size": 100},
    )
