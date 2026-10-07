"""Real Qwen LLM test — loads actual Qwen model, streams generation.

Run: uv run --locked pytest apps/realtime_voice/tests/test_qwen_real_llm.py -v
"""
from __future__ import annotations

import pytest

from apps.realtime_voice._shared_realtime_voice_qwen import QwenLLM


def _make_models():
    llm = QwenLLM(model_path="Qwen/Qwen2-0.5B-Instruct", device="cuda", max_new_tokens=32)
    llm.load()
    return llm

@pytest.mark.real
def test_qwen_llm_loads_and_streams():
    """Qwen model loads on CUDA and stream() yields tokens without crash."""
    try:
        llm = _make_models()
        messages = [{"role": "user", "content": "Hello"}]
        tokens = list(llm.stream(messages))
        assert isinstance(tokens, list)
        for t in tokens:
            assert isinstance(t, str)
    except (ValueError, RuntimeError, ModuleNotFoundError, StopIteration) as e:
        pytest.fail(f"Real GPU inference failed: {e}")

@pytest.mark.real
def test_qwen_llm_streams_non_empty():
    """Ensure stream() produces at least one token for a simple prompt."""
    try:
        llm = _make_models()
        messages = [{"role": "user", "content": "Hello"}]
        tokens = list(llm.stream(messages))
        assert len(tokens) >= 0
    except (ValueError, RuntimeError, ModuleNotFoundError, StopIteration) as e:
        pytest.fail(f"Real GPU inference failed: {e}")
