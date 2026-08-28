import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
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

    @field_validator("ref_audios")
    @classmethod
    def _check_audio_not_alone(cls, v: list[str], info) -> list[str]:
        if v:
            has_visual = bool(info.data.get("ref_images")) or bool(info.data.get("ref_videos"))
            if not has_visual:
                raise ValueError("reference audio requires at least one reference image or video")
        return v


class Output(BaseModel):
    model_config = ConfigDict(title="MiniMaxH3Ref2VAComfyOutput")

    class Artifact(BaseModel):
        model_config = ConfigDict(title="Artifact")
        url: str
        key: str
        size: int

    artifact: Artifact
    video: str


def test_input_valid():
    Input(prompt="a cinematic shot with <Picture 1>", ref_images=["abc"])


def test_input_prompt_required():
    with pytest.raises(ValidationError):
        Input(prompt=None)


def test_ref_images_limit():
    with pytest.raises(ValidationError):
        Input(prompt="test", ref_images=["img"] * 10)


def test_total_files_limit():
    with pytest.raises(ValidationError):
        Input(
            prompt="test",
            ref_images=["img"] * 5,
            ref_videos=["vid"] * 5,
            ref_audios=["aud"] * 3,
        )


def test_audio_without_visual_raises():
    with pytest.raises(ValidationError):
        Input(prompt="test", ref_audios=["aud"])


def test_output_valid():
    Output(
        artifact={"url": "https://r2.example.com/file.mp4", "key": "file.mp4", "size": 100},
        video="dGVzdA==",
    )
