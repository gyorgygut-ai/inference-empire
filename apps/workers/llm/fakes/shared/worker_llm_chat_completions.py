import os
import random
import time
import uuid

from fastapi import FastAPI, HTTPException, Request

REPLIES = (
    "I heard you. Tell me more.",
    "That's interesting - what happened next?",
    "Got it. How would you like to continue?",
)


def build_app() -> FastAPI:
    app = FastAPI(title="worker-llm-local-stub")
    expected_token = os.environ.get("SECRET_LLM_CHAT_COMPLETIONS_API_KEY", "")
    request_count = 0

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/__test__/metrics")
    def metrics() -> dict[str, int]:
        return {"requests": request_count}

    @app.post("/__test__/reset")
    def reset_metrics() -> dict[str, int]:
        nonlocal request_count
        request_count = 0
        return {"requests": request_count}

    @app.post("/v1/chat/completions")
    async def complete(request: Request) -> dict[str, object]:
        nonlocal request_count
        scheme, _, supplied = request.headers.get("authorization", "").partition(" ")
        if scheme.casefold() != "bearer" or not expected_token or supplied != expected_token:
            raise HTTPException(status_code=401, detail="Invalid API key")
        body = await request.json()
        if not isinstance(body, dict) or not isinstance(body.get("messages"), list):
            raise HTTPException(status_code=422, detail="messages is required")
        request_count += 1
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": body.get("model", "configured"),
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": random.choice(REPLIES)},
                    "finish_reason": "stop",
                }
            ],
        }

    return app
