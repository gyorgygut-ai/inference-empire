import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Literal, Optional


class Input(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3Ref2VAComfyInput")
    prompt: str
    ref_images: list[str] = Field(default=[], max_length=9)
    ref_videos: list[str] = Field(default=[], max_length=3)
    ref_video_audios: list[str] = Field(default=[], max_length=3)
    ref_audios: list[str] = Field(default=[], max_length=3)
    width: int = Field(default=1344)
    height: int = Field(default=768)
    length: int = Field(default=124)
    steps: int = Field(default=20)
    seed: Optional[int] = Field(default=None)
    ref_image_size: Literal["match", "max"] = Field(default="match")
    scheduler: Literal["simple", "beta", "normal"] = Field(default="simple")


def test_input_valid():
    Input(prompt="a cinematic shot with <Picture 1>", ref_images=["abc"])


def test_input_prompt_required():
    with pytest.raises(ValidationError):
        Input(prompt=None)


def test_input_defaults():
    inp = Input(prompt="test")
    assert inp.ref_images == []
    assert inp.ref_videos == []
    assert inp.ref_audios == []
    assert inp.width == 1344
    assert inp.height == 768
    assert inp.ref_image_size == "match"
    assert inp.scheduler == "simple"


def test_output_valid():
    from tests.e2e_local.conftest import assert_artifact_nonempty

    artifact = {"url": "https://r2.example.com/file.mp4", "key": "file.mp4", "size": 100}
    assert_artifact_nonempty(artifact)
