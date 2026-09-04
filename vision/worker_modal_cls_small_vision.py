import base64
import io
import re
import time
from typing import Literal

import modal
from pydantic import BaseModel, ConfigDict

REPO_ID = "Qwen/Qwen2-VL-2B-Instruct"

app = modal.App("small-vision-worker")


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


def _build_analyze_prompt() -> str:
    classification = SmallVisionOutput.model_fields["classification"].annotation
    classification_values = ", ".join(f'"{v}"' for v in classification.__args__)
    return f"""Analyze this image. Return valid JSON with exactly these fields:
- classification: one of [{classification_values}]
- subjects: array of strings (describe each main subject including people, e.g., "woman in red dress", "golden retriever")
- description: string (concise natural language description including any visible text)"""


def _download_model():
    import torch
    from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

    Qwen2VLForConditionalGeneration.from_pretrained(REPO_ID, torch_dtype=torch.bfloat16)
    AutoProcessor.from_pretrained(REPO_ID)


image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.9.1",
        "transformers",
        "torchvision",
        "pillow",
        "accelerate",
        "fastapi",
        "hf_transfer",
    )
    .env(
        {
            "HF_HOME": "/root/.cache/huggingface",
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
        }
    )
    .run_function(_download_model)
)


@app.cls(
    image=image,
    gpu="L4",
    scaledown_window=150,
    max_containers=1,
)
class SmallVisionWorker:
    @modal.enter()
    def load(self):
        from services.real_r2 import RealR2Storage
        self.storage = RealR2Storage()

        print("[INIT] loading model Qwen/Qwen2-VL-2B-Instruct", flush=True)
        t0 = time.time()
        import torch
        import torch.distributed as dist

        dist.is_available = lambda: False

        import torch._higher_order_ops.utils as _hoop

        if not hasattr(_hoop, "setup_compilation_env"):
            _hoop.setup_compilation_env = _hoop._set_compilation_env

        from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

        self.torch = torch
        self.analyze_prompt = _build_analyze_prompt()
        self.model = (
            Qwen2VLForConditionalGeneration.from_pretrained(REPO_ID, torch_dtype=torch.bfloat16)
            .to("cuda")
            .eval()
        )
        self.processor = AutoProcessor.from_pretrained(REPO_ID)
        print(f"[INIT] model loaded in {time.time() - t0:.1f}s", flush=True)

    def _run_analyze(self, image_base64: str) -> dict:
        from PIL import Image as PILImage

        req = SmallVisionInput(image_base64=image_base64)
        img = PILImage.open(io.BytesIO(base64.b64decode(req.image_base64))).convert("RGB")

        messages = [{
            "role": "user",
            "content": [
                {"type": "image", "image": img},
                {"type": "text", "text": self.analyze_prompt},
            ],
        }]

        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.processor(text=[text], images=[img], return_tensors="pt").to("cuda")

        from transformers import GenerationConfig

        gen_config = GenerationConfig(
            max_new_tokens=512,
            do_sample=False,
        )

        output_ids = self.model.generate(**inputs, generation_config=gen_config)
        generated = output_ids[0][inputs.input_ids.shape[1] :]
        result = self.processor.decode(generated, skip_special_tokens=True)

        m = re.search(r"\{.*\}", result, re.DOTALL)
        if m:
            return SmallVisionOutput.model_validate_json(m.group()).model_dump()
        return {"raw": result}

    @modal.method()
    def analyze(self, image_base64: str) -> dict:
        try:
            return self._run_analyze(image_base64)
        except Exception as e:
            print(f"[ERR] {type(e).__name__}: {e}", flush=True)
            raise

    @modal.fastapi_endpoint(method="POST")
    def analyze_web(self, item: SmallVisionInput) -> dict:
        try:
            return self._run_analyze(item.image_base64)
        except Exception as e:
            print(f"[ERR] {type(e).__name__}: {e}", flush=True)
            raise