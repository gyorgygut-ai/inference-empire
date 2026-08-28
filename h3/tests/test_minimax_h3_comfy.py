import pytest
from pydantic import BaseModel, ConfigDict, ValidationError
from typing import Optional


class Input(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3ComfyInput")
    prompt: str
    first_frame: Optional[str] = None
    last_frame: Optional[str] = None


class Output(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3ComfyOutput")

    class Artifact(BaseModel):
        model_config = ConfigDict(title="Artifact")
        url: str
        key: str
        size: int

    artifact: Artifact
    video: str


def test_input_valid():
    Input(prompt="a cinematic shot of a cat")


def test_input_prompt_required():
    with pytest.raises(ValidationError):
        Input(prompt=None)


def test_output_valid():
    Output(
        artifact={"url": "https://r2.example.com/file.mp4", "key": "file.mp4", "size": 100},
        video="dGVzdA==",
    )
