import importlib

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Optional


class Input(BaseModel):
    model_config = ConfigDict(title="SmallVisionInput")
    image_base64: str


class Output(BaseModel):
    model_config = ConfigDict(title="SmallVisionOutput")
    classification: str
    subjects: list[str]
    description: str


def test_module_import():
    importlib.import_module("worker_flash_cls_small_vision")


def test_input_valid():
    Input(image_base64="abc")


def test_input_image_required():
    with pytest.raises(ValidationError):
        Input(image_base64=None)


def test_output_valid():
    Output(classification="landscape_0p", subjects=["mountain"], description="a mountain")
