from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient
from dist.contract_voice_llm_chat_completions import Input
from shared.worker_voice_llm_chat_completions import (
    MODELS,
    build_app,
    generate_reply,
)


class FakeInputs(dict):
    def __init__(self) -> None:
        super().__init__()
        self.input_ids = np.array([[10, 11]])

    def to(self, device: str) -> FakeInputs:
        assert device == "cpu"
        return self


class FakeTokenizer:
    def __init__(self) -> None:
        self.messages = None
        self.decode_tokens = None

    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        tokenize: bool,
        add_generation_prompt: bool,
    ) -> str:
        self.messages = messages
        assert tokenize is False
        assert add_generation_prompt is True
        return "prompt"

    def __call__(self, prompt: str, return_tensors: str) -> FakeInputs:
        assert prompt == "prompt"
        assert return_tensors == "pt"
        return FakeInputs()

    def decode(self, tokens: np.ndarray, skip_special_tokens: bool) -> str:
        self.decode_tokens = tokens
        assert skip_special_tokens is True
        return "  generated reply  "


class FakeModel:
    device = "cpu"

    def __init__(self) -> None:
        self.options = None

    def generate(self, **options: object) -> np.ndarray:
        self.options = options
        return np.array([[10, 11, 12, 13]])


def test_input_contract_rejects_empty_messages_and_unknown_fields():
    with pytest.raises(ValueError):
        Input.model_validate({"model": "qwen", "messages": []})
    with pytest.raises(ValueError):
        Input.model_validate(
            {
                "model": "qwen",
                "messages": [{"role": "user", "content": "Hello"}],
                "unexpected": True,
            }
        )


def test_model_configuration_uses_url_and_cache_path_mapping():
    assert MODELS == {
        "qwen2_5_3b_instruct": {
            "url": "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct",
            "path": "./model-cache/qwen2_5_3b_instruct",
        }
    }


def test_generate_reply_formats_messages_and_returns_token_usage():
    tokenizer = FakeTokenizer()
    model = FakeModel()
    request = Input(
        model="qwen",
        messages=[{"role": "user", "content": "Hello"}],
        temperature=0,
    )

    reply, prompt_tokens, completion_tokens = generate_reply(
        request,
        {"model": model, "tokenizer": tokenizer},
    )

    assert reply == "generated reply"
    assert (prompt_tokens, completion_tokens) == (2, 2)
    assert tokenizer.messages == [{"role": "user", "content": "Hello"}]
    assert model.options == {"max_new_tokens": 128, "do_sample": False}


def test_chat_completions_returns_openai_compatible_output():
    app = build_app(generator=lambda _: ("A deterministic reply.", 3, 4))
    response = TestClient(app).post(
        "/v1/chat/completions",
        json={
            "model": "qwen",
            "messages": [{"role": "user", "content": "Hello"}],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"] == {
        "role": "assistant",
        "content": "A deterministic reply.",
    }
    assert body["usage"] == {
        "prompt_tokens": 3,
        "completion_tokens": 4,
        "total_tokens": 7,
    }


def test_chat_completions_rejects_invalid_request_and_empty_reply():
    app = build_app(generator=lambda _: ("", 1, 0))
    client = TestClient(app)
    invalid = client.post(
        "/v1/chat/completions",
        json={"model": "qwen", "messages": []},
    )
    empty = client.post(
        "/v1/chat/completions",
        json={
            "model": "qwen",
            "messages": [{"role": "user", "content": "Hello"}],
        },
    )

    assert invalid.status_code == 422
    assert empty.status_code == 502
