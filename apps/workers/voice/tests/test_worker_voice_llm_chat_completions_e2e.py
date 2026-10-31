from fastapi.testclient import TestClient
from shared.worker_voice_llm_chat_completions import build_app


def test_local_chat_completions_request_returns_reply():
    app = build_app(generator=lambda _: ("Local reply.", 2, 2), api_key="local-llm-key")
    client = TestClient(app)
    health = client.get("/health")
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer local-llm-key"},
        json={
            "model": "qwen",
            "messages": [
                {"role": "system", "content": "Be concise."},
                {"role": "user", "content": "Say hello."},
            ],
        },
    )

    assert health.status_code == 200
    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "Local reply."
