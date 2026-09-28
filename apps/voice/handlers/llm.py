"""Language-model handler: Qwen2.5-3B-Instruct via transformers, INT4.

Loaded once in ``on_start``. ``stream`` yields text tokens incrementally using
``TextIteratorStreamer`` in a worker thread, and honours an external cancel
event for barge-in. A lock serializes GPU access across concurrent sessions.
"""

from __future__ import annotations

import threading
from typing import Any, cast


class QwenLLM:
    def __init__(
        self,
        model_path: str,
        device: str = "cuda",
        quantize: str = "int4",
        max_new_tokens: int = 256,
    ) -> None:
        self.model_path = model_path
        self.device = device
        self.quantize = quantize
        self.max_new_tokens = max_new_tokens
        self.model: Any = None
        self.tokenizer = None
        self._lock = threading.Lock()

    def load(self) -> QwenLLM:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        use_quant = self.device == "cuda" and self.quantize == "int4"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        if use_quant:
            from transformers import BitsAndBytesConfig

            quant_config = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                device_map="auto",
                quantization_config=quant_config,
                torch_dtype=torch.bfloat16,
            )
        else:
            model = cast(
                "Any",
                AutoModelForCausalLM.from_pretrained(
                    self.model_path, torch_dtype=torch.float16
                ),
            )
            self.model = model.to(self.device)
        return self

    def stream(self, messages: list[dict], cancel=None, max_new_tokens: int | None = None):
        """Yield text tokens for ``messages``. Stops early if ``cancel`` is set.

        ``cancel`` may be a ``threading.Event`` or ``asyncio.Event`` exposing
        ``is_set()``.
        """
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("LLM not loaded; call load() first")

        import threading

        from transformers import TextIteratorStreamer

        max_tokens = max_new_tokens or self.max_new_tokens
        inputs = self.tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, return_tensors="pt"
        ).to(self.model.device)

        streamer = TextIteratorStreamer(
            self.tokenizer, skip_prompt=True, skip_special_tokens=True
        )
        gen_kwargs: dict[str, Any] = {"inputs": inputs, "streamer": streamer, "max_new_tokens": max_tokens}

        def generate():
            with self._lock:
                self.model.generate(**gen_kwargs)

        t = threading.Thread(target=generate)
        t.start()
        try:
            for token in streamer:
                if cancel is not None and cancel.is_set():
                    break
                yield token
        finally:
            t.join()
