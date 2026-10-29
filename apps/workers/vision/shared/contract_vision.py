from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from .validation import validate_image_b64


class SmallVisionInput(BaseModel):
    model_config = ConfigDict(title="SmallVisionInput")
    image_base64: str
    prompt: str | None = Field(
        default=None,
        description="Custom analyze instruction override. Null uses built-in default.",
    )

    @field_validator("image_base64")
    @classmethod
    def _check_image(cls, v: str, info: ValidationInfo) -> str:
        return validate_image_b64(v, info.field_name or "image")


class SmallVisionOutput(BaseModel):
    model_config = ConfigDict(title="SmallVisionOutput")
    classification: Literal[
        "portrait_0p",
        "portrait_1p",
        "portrait_2p",
        "portrait_3p",
        "portrait_group",
        "selfie_1p",
        "selfie_2p",
        "selfie_group",
        "group_photo_2p",
        "group_photo_3p",
        "group_photo_4p",
        "group_photo_5p_plus",
        "group_photo_group",
        "food_0p",
        "document_0p",
        "landscape_0p",
        "animal_0p",
        "object_0p",
        "screenshot_0p",
        "receipt_0p",
        "other_0p",
    ]
    subjects: list[str]
    description: str
