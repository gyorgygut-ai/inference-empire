from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from .validation import validate_image_b64


class Flux2Klein9bInput(BaseModel):
    model_config = ConfigDict(title="Flux2Klein9bInput")
    prompt: str
    height: int = Field(default=512)
    width: int = Field(default=512)
    guidance_scale: float = Field(default=1.0)
    num_inference_steps: int = Field(default=4)
    seed: int | None = Field(default=None)
    input_image: str | None = Field(default=None)
    reference_images: list[str] = Field(default=[])

    @field_validator("input_image")
    @classmethod
    def _check_input_image(cls, v: str | None, info: ValidationInfo) -> str | None:
        if v is None:
            return None
        return validate_image_b64(v, info.field_name or "image")

    @field_validator("reference_images")
    @classmethod
    def _check_reference_images(cls, v: list[str], info: ValidationInfo) -> list[str]:
        return [validate_image_b64(item, f"{info.field_name}[{i}]") for i, item in enumerate(v)]


class Artifact(BaseModel):
    model_config = ConfigDict(title="Artifact")
    presigned_url: str


class Flux2Klein9bOutput(BaseModel):
    model_config = ConfigDict(title="Flux2Klein9bOutput")
    artifact: Artifact
