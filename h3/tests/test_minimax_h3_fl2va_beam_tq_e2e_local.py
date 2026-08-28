import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class MiniMaxH3Fl2VAInput(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3Fl2VAInput")
    prompt: str
    first_frame: str
    prompt_style: str = Field(default="style_a")
    num_frames: int = Field(default=97)
    guidance_scale: float = Field(default=5.0)
    seed: int | None = Field(default=None)
    steps: int = Field(default=30)


def test_input_valid():
    MiniMaxH3Fl2VAInput(prompt="a scene", first_frame="abc")


def test_input_prompt_required():
    with pytest.raises(ValidationError):
        MiniMaxH3Fl2VAInput(prompt=None, first_frame="abc")
