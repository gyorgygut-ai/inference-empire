from dist.contract_llm_chat_completions import Input


def llm_generator_stub(request: Input) -> tuple[str, int, int]:
    """Deterministic LLM stub returning a predictable reply and token counts."""
    transcript = request.messages[-1].content if request.messages else ""
    reply_text = f"LLM response to: {transcript[:20]}"
    prompt_tokens = sum(len(message.content.split()) for message in request.messages)
    completion_tokens = len(reply_text.split())
    return reply_text, prompt_tokens, completion_tokens
