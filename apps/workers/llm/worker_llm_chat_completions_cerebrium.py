"""Cerebrium ASGI wrapper for the OpenAI-compatible LLM worker."""

from shared.worker_llm_chat_completions import build_app

app = build_app()

__all__ = ["app"]
