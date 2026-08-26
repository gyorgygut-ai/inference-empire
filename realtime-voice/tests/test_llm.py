"""LLM handler test — skipped unless model tests are explicitly enabled.

Heavy (loads Qwen3-8B INT4 + needs a GPU). Run in the Beam container with
``BEAM_VOICE_TEST_MODELS=1`` and ``LLM_MODEL_PATH`` pointing at the seeded
volume path.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("transformers")

from handlers.llm import QwenLLM  # noqa: E402


@pytest.mark.skipif(
    os.environ.get("BEAM_VOICE_TEST_MODELS") != "1",
    reason="set BEAM_VOICE_TEST_MODELS=1 and LLM_MODEL_PATH to run",
)
def test_stream_yields_text():
    path = os.environ["LLM_MODEL_PATH"]
    llm = QwenLLM(path).load()
    messages = [{"role": "user", "content": "Say 'hi' in one word."}]
    out = "".join(llm.stream(messages, max_new_tokens=16))
    assert len(out.strip()) > 0
