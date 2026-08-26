import base64
import io
import re
from typing import Literal

from PIL import Image as PILImage
from pydantic import BaseModel, ConfigDict, Field

from beam import Image, QueueDepthAutoscaler, Volume, endpoint

CACHE_PATH = "./hf-cache"

image = (
    Image(python_version="python3.11")
    .add_python_packages([
        "torch==2.9.1",
        "transformers>=4.57,<5",
        "torchvision",
        "pillow",
        "accelerate",
    ])
    .with_envs({
        "HF_HOME": CACHE_PATH,
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
    })
)


class SmallVisionInput(BaseModel):
    model_config = ConfigDict(title="SmallVisionInput")
    image_base64: str


class SmallVisionOutput(BaseModel):
    model_config = ConfigDict(title="SmallVisionOutput")
    classification: Literal[
        "portrait_0p", "portrait_1p", "portrait_2p", "portrait_3p",
        "portrait_group", "selfie_1p", "selfie_2p", "selfie_group",
        "group_photo_2p", "group_photo_3p", "group_photo_4p",
        "group_photo_5p_plus", "group_photo_group", "food_0p",
        "document_0p", "landscape_0p", "animal_0p", "object_0p",
        "screenshot_0p", "receipt_0p", "other_0p",
    ]
    subjects: list[str]
    description: str


def _build_analyze_prompt() -> str:
    classification = SmallVisionOutput.model_fields["classification"].annotation
    classification_values = ", ".join(f'"{v}"' for v in classification.__args__)
    return f"""Analyze this image. Return valid JSON with exactly these fields:
- classification: one of [{classification_values}]
- subjects: array of strings (describe each main subject including people, e.g., "woman in red dress", "golden retriever")
- description: string (concise natural language description including any visible text)"""


def load_models():
    import torch
    import torch.distributed as dist
    dist.is_available = lambda: False

    import torch._higher_order_ops.utils as _hoop
    if not hasattr(_hoop, "setup_compilation_env"):
        _hoop.setup_compilation_env = _hoop._set_compilation_env

    from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

    model = Qwen2VLForConditionalGeneration.from_pretrained(
        "Qwen/Qwen2-VL-2B-Instruct",
        torch_dtype=torch.bfloat16,
        device_map="auto",
        cache_dir=CACHE_PATH,
    ).eval()

    processor = AutoProcessor.from_pretrained(
        "Qwen/Qwen2-VL-2B-Instruct",
        cache_dir=CACHE_PATH,
    )

    return model, processor, _build_analyze_prompt()


@endpoint(
    name="small-vision-worker",
    cpu=2,
    memory="16Gi",
    gpu="A10G",
    image=image,
    on_start=load_models,
    volumes=[Volume(name="hf-cache", mount_path=CACHE_PATH)],
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=0,
    checkpoint_enabled=True,
)
def analyze(context, image_base64: str):
    model, processor, analyze_prompt = context.on_start_value

    req = SmallVisionInput(image_base64=image_base64)
    img = PILImage.open(io.BytesIO(base64.b64decode(req.image_base64))).convert("RGB")

    messages = [{
        "role": "user",
        "content": [
            {"type": "image", "image": img},
            {"type": "text", "text": analyze_prompt},
        ],
    }]

    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = processor(text=[text], images=[img], return_tensors="pt").to("cuda")

    from transformers import GenerationConfig
    gen_config = GenerationConfig(
        response_format={"type": "json_object"},
        max_new_tokens=512,
        do_sample=False,
    )

    output_ids = model.generate(**inputs, generation_config=gen_config)
    generated = output_ids[0][inputs.input_ids.shape[1]:]
    result = processor.decode(generated, skip_special_tokens=True)

    m = re.search(r"\{.*\}", result, re.DOTALL)
    if m:
        return SmallVisionOutput.model_validate_json(m.group()).model_dump()
    return {"raw": result}
