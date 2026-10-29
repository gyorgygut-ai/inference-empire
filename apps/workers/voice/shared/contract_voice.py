"""Voice worker request and response contracts."""

from pydantic import BaseModel, ConfigDict, Field


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audio: str
    sample_rate: int = Field(default=24_000, gt=0)
    voice: str = "builtin"
    language: str = "en"


class Output(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transcript: str
    response: str
    audio: str
    sample_rate: int = 24_000
