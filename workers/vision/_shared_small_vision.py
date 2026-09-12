"""Shared business logic for small-vision. No platform imports."""
from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationInfo, field_validator

from workers.services.media.validation import validate_image_b64

REPO_ID = "Qwen/Qwen2-VL-2B-Instruct"
MAX_NEW_TOKENS = 512

# Single source of truth for ALL provider image pip deps (modal/beam/flash).
# Worker files must reference this list, never inline their own pins.
# Pre-deploy gate: uv run python -c "from workers.vision._shared_small_vision import IMAGE_PIP_DEPS; print('\n'.join(IMAGE_PIP_DEPS))" | uv pip compile --python-version 3.11 -
IMAGE_PIP_DEPS: list[str] = [
    "torch==2.9.1",
    "transformers==5.16.1",
    "torchvision==0.24.1",
    "pillow==12.3.0",
    "accelerate==1.14.0",
    "boto3==1.43.83",
    "fastapi==0.141.1",
    "hf_transfer==0.1.9",
]


def _load_dotenv() -> None:
    path = Path(__file__).parent.parent / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


class SmallVisionInput(BaseModel):
    model_config = ConfigDict(title="SmallVisionInput")
    image_base64: str

    @field_validator("image_base64")
    @classmethod
    def _check_image(cls, v: str, info: ValidationInfo) -> str:
        return validate_image_b64(v, info.field_name)

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

def build_analyze_prompt() -> str:
    classification = SmallVisionOutput.model_fields["classification"].annotation
    classification_values = ", ".join(f'"{v}"' for v in classification.__args__)
    return f"""Analyze this image. Return valid JSON with exactly these fields:
- classification: one of [{classification_values}]
- subjects: array of strings (describe each main subject including people, e.g., "woman in red dress", "golden retriever")
- description: string (concise natural language description including any visible text)"""

def load_models(cache_dir=None):
    """Production path: always boots the real model."""
    print(f"[INIT] loading model {REPO_ID}", flush=True)
    t0 = time.time()
    import torch
    import torch.distributed as dist

    def _dist_unavailable() -> bool:
        return False

    dist.is_available = _dist_unavailable

    import torch._higher_order_ops.utils as _hoop

    if not hasattr(_hoop, "setup_compilation_env"):
        _hoop.setup_compilation_env = _hoop._set_compilation_env

    from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

    from_kwargs = {"torch_dtype": torch.bfloat16, "device_map": "auto"}
    if cache_dir:
        from_kwargs["cache_dir"] = cache_dir
    model = Qwen2VLForConditionalGeneration.from_pretrained(REPO_ID, **from_kwargs).eval()

    proc_kwargs = {}
    if cache_dir:
        proc_kwargs["cache_dir"] = cache_dir
    processor = AutoProcessor.from_pretrained(REPO_ID, **proc_kwargs)

    print(f"[INIT] model loaded in {time.time() - t0:.1f}s", flush=True)
    return model, processor, build_analyze_prompt()

def do_inference(model, processor, analyze_prompt: str, req: SmallVisionInput):
    """Takes validated Input, returns Output. Testable via DI."""
    import base64
    import io

    from PIL import Image as PILImage

    t_req = time.time()
    print(f"[REQ] image_bytes={len(req.image_base64)}", flush=True)

    img = PILImage.open(io.BytesIO(base64.b64decode(req.image_base64))).convert("RGB")

    messages = [{"role": "user", "content": [
        {"type": "image", "image": img},
        {"type": "text", "text": analyze_prompt},
    ]}]

    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = processor(text=[text], images=[img], return_tensors="pt").to("cuda")

    from transformers import GenerationConfig

    gen_config = GenerationConfig(
        response_format={"type": "json_object"},
        max_new_tokens=MAX_NEW_TOKENS,
        do_sample=False,
    )

    print("[GEN] starting inference", flush=True)
    t_gen = time.time()
    output_ids = model.generate(**inputs, generation_config=gen_config)
    print(f"[GEN] inference done in {time.time() - t_gen:.1f}s", flush=True)
    generated = output_ids[0][inputs.input_ids.shape[1]:]
    result = processor.decode(generated, skip_special_tokens=True)

    m = re.search(r"\{.*\}", result, re.DOTALL)
    print(f"[OK] completed in {time.time() - t_req:.1f}s", flush=True)
    if not m:
        raise RuntimeError(f"vision model returned non-JSON: {result[:200]!r}")
    return SmallVisionOutput.model_validate_json(m.group())

def load_dependencies(cache_dir=None):
    """Load all dependencies for small-vision worker."""
    model, processor, analyze_prompt = load_models(cache_dir=cache_dir)
    return model, processor, analyze_prompt
