from __future__ import annotations

import os
import re
import time
from pathlib import Path

from .contract_vision import SmallVisionInput, SmallVisionOutput

REPO_ID = "Qwen/Qwen2-VL-2B-Instruct"
MAX_NEW_TOKENS = 512

DEPENDENCIES = [
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


def build_analyze_prompt() -> str:
    classification = SmallVisionOutput.model_fields["classification"].annotation
    classification_values = ", ".join(f'"{v}"' for v in classification.__args__)
    return f"""Analyze this image. Return valid JSON with exactly these fields:
- classification: one of [{classification_values}]
- subjects: array of strings (describe each main subject including people, e.g., "woman in red dress", "golden retriever")
- description: string (concise natural language description including any visible text)"""


def resolve_analyze_prompt(loaded_default: str, override: str | None) -> str:
    """Return caller override when set, else the built-in default prompt."""
    return override if override else loaded_default

def load_models(cache_dir=None):
    """Production path: always boots the real model."""
    print(f"[INIT] loading model {REPO_ID}", flush=True)
    t0 = time.time()
    import torch
    import torch.distributed as dist

    def _dist_unavailable() -> bool:
        return False

    dist.is_available = _dist_unavailable  # ty: ignore[invalid-assignment]

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
