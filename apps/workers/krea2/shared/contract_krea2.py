from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from .validation import validate_image_b64


class Krea2Ref2ImgInput(BaseModel):
    model_config = ConfigDict(title="Krea2Ref2ImgInput")
    prompt: str
    reference_image: str | None = Field(default=None)

    @field_validator("reference_image")
    @classmethod
    def _check_reference_image(cls, v: str | None, info: ValidationInfo) -> str | None:
        if v is None:
            return None
        return validate_image_b64(v, info.field_name or "image")
    height: int = Field(default=768)
    width: int = Field(default=768)
    num_inference_steps: int = Field(default=8)
    guidance_scale: float = Field(default=0.0)
    seed: int | None = Field(default=None)
    lora_scale: float = Field(default=1.0)
    face_crop: bool = Field(default=True)


class Artifact(BaseModel):
    model_config = ConfigDict(title="Artifact")
    presigned_url: str


class Krea2Ref2ImgOutput(BaseModel):
    model_config = ConfigDict(title="Krea2Ref2ImgOutput")
    artifact: Artifact
