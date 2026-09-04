"""Shared business logic for small-vision. No platform imports."""
from __future__ import annotations

import re
import time
from typing import Literal

from pydantic import BaseModel, ConfigDict

REPO_ID = "Qwen/Qwen2-VL-2B-Instruct"
MAX_NEW_TOKENS = 512


class SmallVisionInput(BaseModel):
    model_config = ConfigDict(title="SmallVisionInput")
    image_base64: str


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

    dist.is_available = lambda: False

    import torch._higher_order_ops.utils as _hoop

    if not hasattr(_hoop, "setup_compilation_env"):
        _hoop.setup_compilation_env = _hoop._set_compilation_env

    from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

    from_kwargs = dict(torch_dtype=torch.bfloat16, device_map="auto")
    if cache_dir:
        from_kwargs["cache_dir"] = cache_dir
    model = Qwen2VLForConditionalGeneration.from_pretrained(REPO_ID, **from_kwargs).eval()

    proc_kwargs = {}
    if cache_dir:
        proc_kwargs["cache_dir"] = cache_dir
    processor = AutoProcessor.from_pretrained(REPO_ID, **proc_kwargs)

    print(f"[INIT] model loaded in {time.time() - t0:.1f}s", flush=True)
    return model, processor, build_analyze_prompt()


def load_models_as_needed(model=None, processor=None, analyze_prompt=None, cache_dir=None):
    """DI entry: injected fakes pass through, else real load."""
    if model is not None:
        return model, processor, analyze_prompt or build_analyze_prompt()
    return load_models(cache_dir=cache_dir)


def run_analyze(model, processor, analyze_prompt: str, req: SmallVisionInput):
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
    if m:
        return SmallVisionOutput.model_validate_json(m.group())
    return {"raw": result}
