import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Literal, Optional


class MiniMaxH3Ref2VAInput(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3Ref2VAInput")
    prompt: str
    ref_images: list[str] = Field(default=[], max_length=9)
    ref_audios: list[str] = Field(default=[], max_length=3)
    width: int = Field(default=1344)
    height: int = Field(default=768)
    length: int = Field(default=124)
    steps: int = Field(default=20)
    seed: Optional[int] = Field(default=None)
    scheduler: Literal["simple", "beta", "normal"] = Field(default="simple")


def test_input_valid():
    MiniMaxH3Ref2VAInput(prompt="a scene", ref_images=["abc"])


def test_input_prompt_required():
    with pytest.raises(ValidationError):
        MiniMaxH3Ref2VAInput(prompt=None)
