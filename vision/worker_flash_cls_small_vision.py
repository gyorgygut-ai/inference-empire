import os
import time

from runpod_flash import Endpoint, GpuGroup


@Endpoint(
    name="small-vision-worker",
    gpu=[GpuGroup.AMPERE_16],
    workers=(0, 1),
    idle_timeout=5,
    flashboot=True,
    env={
        "HF_HOME": "/runpod-volume/huggingface-cache",
    },
    dependencies=[
        "torch==2.9.1",
        "transformers>=4.57,<5",
        "torchvision",
        "pillow",
        "accelerate",
    ],
)
class Qwen2VLVisionWorker:
    # --- BEGIN CONTRACT: small_vision (generated; run make gen-contracts) ---
    from pydantic import BaseModel

    class Input(BaseModel):
        from typing import Literal as _Literal, Optional as _Optional
        from pydantic import BaseModel as _BaseModel, ConfigDict as _ConfigDict, Field as _Field

        model_config = _ConfigDict(title='SmallVisionInput')
        image_base64: str

    class Output(BaseModel):
        from typing import Literal as _Literal, Optional as _Optional
        from pydantic import BaseModel as _BaseModel, ConfigDict as _ConfigDict, Field as _Field

        model_config = _ConfigDict(title='SmallVisionOutput')
        classification: _Literal['portrait_0p', 'portrait_1p', 'portrait_2p', 'portrait_3p', 'portrait_group', 'selfie_1p', 'selfie_2p', 'selfie_group', 'group_photo_2p', 'group_photo_3p', 'group_photo_4p', 'group_photo_5p_plus', 'group_photo_group', 'food_0p', 'document_0p', 'landscape_0p', 'animal_0p', 'object_0p', 'screenshot_0p', 'receipt_0p', 'other_0p']
        subjects: list[str]
        description: str
    # --- END CONTRACT: small_vision ---





















    def __init__(self):
        import torch.distributed as dist
        dist.is_available = lambda: False

        print("[INIT] loading model Qwen/Qwen2-VL-2B-Instruct", flush=True)
        t0 = time.time()

        import torch._higher_order_ops.utils as _hoop
        if not hasattr(_hoop, "setup_compilation_env"):
            _hoop.setup_compilation_env = _hoop._set_compilation_env

        import torch
        from transformers import Qwen2VLForConditionalGeneration, AutoProcessor

        classification = self.Output.model_fields["classification"].annotation
        classification_values = ", ".join(f'"{v}"' for v in classification.__args__)
        self.analyze_prompt = f"""Analyze this image. Return valid JSON with exactly these fields:
- classification: one of [{classification_values}]
- subjects: array of strings (describe each main subject including people, e.g., "woman in red dress", "golden retriever")
- description: string (concise natural language description including any visible text)"""

        self.torch = torch
        self.model = Qwen2VLForConditionalGeneration.from_pretrained(
            "Qwen/Qwen2-VL-2B-Instruct",
            torch_dtype=torch.bfloat16,
            device_map="auto",
        ).eval()
        self.processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-2B-Instruct")
        print(f"[INIT] model loaded in {time.time() - t0:.1f}s", flush=True)

    def _prepare_image(self, base64_str: str):
        import base64
        import io
        from PIL import Image

        img = Image.open(io.BytesIO(base64.b64decode(base64_str))).convert("RGB")
        return img

    def analyze(self, image_base64: str) -> dict:
        try:
            t_req = time.time()
            print("[REQ] image_base64 provided", flush=True)
            req = self.Input(image_base64=image_base64)
        image = self._prepare_image(req.image_base64)

        messages = [{
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": self.analyze_prompt},
            ]
        }]

        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.processor(text=[text], images=[image], return_tensors="pt").to("cuda")

        from transformers import GenerationConfig
        gen_config = GenerationConfig(
            response_format={"type": "json_object"},
            max_new_tokens=512,
            do_sample=False,
        )

        print(f"[GEN] starting inference", flush=True)
        t_gen = time.time()
        output_ids = self.model.generate(**inputs, generation_config=gen_config)
        generated = output_ids[0][inputs.input_ids.shape[1]:]
        print(f"[GEN] inference done in {time.time() - t_gen:.1f}s", flush=True)
        result = self.processor.decode(generated, skip_special_tokens=True)

        import re
        m = re.search(r'\{.*\}', result, re.DOTALL)
        if m:
            print(f"[OK] completed in {time.time() - t_req:.1f}s", flush=True)
            return self.Output.model_validate_json(m.group()).model_dump()
        except Exception as e:
            print(f"[ERR] {type(e).__name__}: {e}", flush=True)
            raise
        return {"raw": result}