from pydantic import BaseModel, ConfigDict, Field


class TinySDInput(BaseModel):
    model_config = ConfigDict(title="TinySDInput")
    prompt: str
    negative_prompt: str = Field(default="")
    height: int = Field(default=512)
    width: int = Field(default=512)
    num_inference_steps: int = Field(default=20)
    guidance_scale: float = Field(default=7.5)
    seed: int | None = Field(default=None)


class Artifact(BaseModel):
    model_config = ConfigDict(title="Artifact")
    presigned_url: str


class TinySDOutput(BaseModel):
    model_config = ConfigDict(title="TinySDOutput")
    artifact: Artifact
