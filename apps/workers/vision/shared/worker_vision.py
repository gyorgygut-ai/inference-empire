from __future__ import annotations

import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

from dist.contract_vision import Input as SmallVisionInput
from dist.contract_vision import Output as SmallVisionOutput

from .validation import validate_image_b64

MODEL_CACHES = {
    "qwen2_vl_2b_instruct": {
        "url": "https://huggingface.co/Qwen/Qwen2-VL-2B-Instruct",
        "path": "./model-cache/qwen2_vl_2b_instruct",
    }
}
MODEL_NAME = "qwen2_vl_2b_instruct"
REPO_ID = urlparse(MODEL_CACHES[MODEL_NAME]["url"]).path.strip("/")
MAX_NEW_TOKENS = 512

DEPENDENCIES = [
"torch==2.9.1",
"transformers==5.16.1",
"torchvision==0.24.1",
"pillow==12.3.0",
    "accelerate==1.14.0",
    "boto3==1.43.83",
    "fastapi==0.141.1",
]

def model_volumes():
    from beam import Volume

    return [
        Volume(name=f"model-cache-{name}", mount_path=model["path"])
        for name, model in MODEL_CACHES.items()
    ]


def download_models() -> dict[str, Path]:
    """Download declared models into their mounted cache paths."""
    from huggingface_hub import snapshot_download

    return {
        name: Path(
            snapshot_download(
                repo_id=urlparse(model["url"]).path.strip("/"),
                cache_dir=model["path"],
                token=os.environ["SECRET_HUGGINGFACE_TOKEN"],
            )
        )
        for name, model in MODEL_CACHES.items()
    }


def build_analyze_prompt() -> str:
    classification = SmallVisionOutput.model_fields["classification"].annotation
    classification_values = ", ".join(f'"{value}"' for value in classification.__args__)
    return f"""Analyze this image. Return valid JSON with exactly these fields:
- classification: one of [{classification_values}]
- subjects: array of strings (describe each main subject including people, e.g., "woman in red dress", "golden retriever")
- description: string (concise natural language description including any visible text)"""


def resolve_analyze_prompt(loaded_default: str, override: str | None) -> str:
    """Return caller override when set, else the built-in default prompt."""
    return override if override else loaded_default

def load_pipeline_lazy():
    """Lazy load model on first request (not at startup)."""
    print(f"[INIT] lazily loading model {REPO_ID}", flush=True)
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

    model_dir = download_models()[MODEL_NAME]
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        str(model_dir), torch_dtype=torch.bfloat16, device_map="auto"
    ).eval()
    processor = AutoProcessor.from_pretrained(str(model_dir))

    print(f"[INIT] model loaded lazily in {time.time() - t0:.1f}s", flush=True)
    return model, processor, build_analyze_prompt()

def do_inference(model, processor, analyze_prompt: str, req: SmallVisionInput):
    """Takes validated Input, returns Output. Testable via DI."""
    import base64
    import io

    from PIL import Image as PILImage

    t_req = time.time()
    print(f"[REQ] image_bytes={len(req.image_base64)}", flush=True)

    image_b64 = validate_image_b64(req.image_base64, "image_base64")
    img = PILImage.open(io.BytesIO(base64.b64decode(image_b64))).convert("RGB")

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
        temperature=1.0,
        top_p=1.0,
        top_k=50,
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

def load_dependencies():
    """Load all dependencies for vision worker (model loaded lazily)."""
    # Model pipeline loaded lazily on first do_inference() request
    return None, None, None
