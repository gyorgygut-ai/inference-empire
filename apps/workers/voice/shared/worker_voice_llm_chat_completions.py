from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException

from dist.contract_voice_llm_chat_completions import (
    Choice,
    Input,
    Output,
    ResponseMessage,
    Usage,
)

if TYPE_CHECKING:
    from collections.abc import Callable

MODELS = {
    "qwen2_5_3b_instruct": {
        "url": "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct",
        "path": "./model-cache/qwen2_5_3b_instruct",
    },
}
MODEL_LOCK = threading.RLock()
MODEL_STATE: dict[str, Any] | None = None
logger = logging.getLogger(__name__)


def load_model() -> dict[str, Any]:
    global MODEL_STATE

    with MODEL_LOCK:
        if MODEL_STATE is not None:
            return MODEL_STATE

        import torch
        from huggingface_hub import snapshot_download
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
        )

        model_path = Path(
            snapshot_download(
                repo_id=urlparse(
                    MODELS["qwen2_5_3b_instruct"]["url"]
                ).path.strip("/"),
                cache_dir=MODELS["qwen2_5_3b_instruct"]["path"],
                token=os.getenv("HF_TOKEN"),
            )
        )
        use_cuda = torch.cuda.is_available()
        options: dict[str, Any] = {
            "device_map": "auto",
            "torch_dtype": torch.float32,
        }

        if use_cuda:
            options["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
            )
            options["torch_dtype"] = torch.bfloat16

        MODEL_STATE = {
            "model": AutoModelForCausalLM.from_pretrained(
                str(model_path),
                **options,
            ),
            "tokenizer": AutoTokenizer.from_pretrained(str(model_path)),
        }
        return MODEL_STATE


def generate_reply(
    request: Input,
    model_state: dict[str, Any] | None = None,
) -> tuple[str, int, int]:
    state = model_state if model_state is not None else load_model()
    tokenizer = state["tokenizer"]
    model = state["model"]
    prompt = tokenizer.apply_chat_template(
        [message.model_dump() for message in request.messages],
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    generation_options: dict[str, Any] = {
        "max_new_tokens": request.max_tokens,
        "do_sample": request.temperature > 0,
    }

    if request.temperature > 0:
        generation_options["temperature"] = request.temperature

    with MODEL_LOCK:
        generated = model.generate(**inputs, **generation_options)

    prompt_tokens = int(inputs.input_ids.shape[-1])
    completion_tokens = int(generated.shape[-1] - prompt_tokens)
    reply = tokenizer.decode(
        generated[0][prompt_tokens:],
        skip_special_tokens=True,
    ).strip()

    if not reply:
        raise ValueError("Qwen returned an empty response")

    return reply, prompt_tokens, completion_tokens


def build_app(
    generator: Callable[[Input], tuple[str, int, int]] = generate_reply,
) -> FastAPI:
    app = FastAPI(title="workers-voice-llm-chat-completions")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/chat/completions", response_model=Output)
    def chat_completions(request: Input) -> Output:
        try:
            content, prompt_tokens, completion_tokens = generator(request)
        except ValueError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
        except Exception as error:
            logger.exception("Chat Completions generation failed")
            raise HTTPException(
                status_code=500,
                detail="Chat Completions generation failed",
            ) from error

        if not content.strip():
            raise HTTPException(
                status_code=502,
                detail="Chat Completions generation returned an empty reply",
            )

        return Output(
            id=f"chatcmpl-{uuid.uuid4().hex}",
            object="chat.completion",
            created=int(time.time()),
            model=request.model,
            choices=[
                Choice(
                    index=0,
                    message=ResponseMessage(role="assistant", content=content),
                    finish_reason="stop",
                )
            ],
            usage=Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
        )

    return app
