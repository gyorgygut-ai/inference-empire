import os

import pytest
from fastapi.testclient import TestClient
from shared.worker_llm_chat_completions import build_app
from tests.stub_services import llm_generator_stub

LLM_API_KEY = "llm-test-key"


@pytest.fixture
def client():
    os.environ["SECRET_LLM_CHAT_COMPLETIONS_API_KEY"] = LLM_API_KEY
    app = build_app(generator=llm_generator_stub)
    return TestClient(app)


def test_llm_health_returns_200(client):
    r = client.get("/health")
    assert r.status_code == 200, "health check failed"


def test_llm_health_response_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_llm_missing_or_invalid_token_returns_401(client):
    # Missing auth header
    r = client.post(
        "/v1/chat/completions",
        json={"model": "qwen2_5_3b_instruct", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 401, "missing token not rejected"

    # Invalid token
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer bad"},
        json={"model": "qwen2_5_3b_instruct", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 401, "invalid token not rejected"


def test_llm_missing_or_invalid_token_response_error(client):
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer bad"},
        json={"model": "qwen2_5_3b_instruct", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 401
    assert "detail" in r.json(), "missing detail in error response"


def test_llm_malformed_messages_returns_422(client):
    # Payload missing required 'messages' field
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {LLM_API_KEY}"},
        json={"model": "qwen2_5_3b_instruct"},
    )
    assert r.status_code == 422, "malformed payload not rejected"


def test_llm_malformed_messages_response_error(client):
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {LLM_API_KEY}"},
        json={"model": "qwen2_5_3b_instruct"},
    )
    assert r.status_code == 422
    assert "detail" in r.json(), "missing detail in error response"


def test_llm_valid_messages_returns_200(client):
    payload = {
        "model": "qwen2_5_3b_instruct",
        "messages": [{"role": "user", "content": "hi"}],
    }
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {LLM_API_KEY}"},
        json=payload,
    )
    assert r.status_code == 200, "valid messages request failed"


def test_llm_valid_messages_response_content_non_empty(client):
    payload = {
        "model": "qwen2_5_3b_instruct",
        "messages": [{"role": "user", "content": "hi"}],
    }
    r = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {LLM_API_KEY}"},
        json=payload,
    )
    assert r.status_code == 200
    data = r.json()
    choices = data.get("choices", [])
    assert len(choices) >= 1, "no choices returned"
    content = choices[0].get("message", {}).get("content", "")
    assert isinstance(content, str) and content.strip(), "empty completion"


def test_llm_forwards_each_request_history_without_retaining_prior_messages():
    received_messages = []

    def recording_generator(request):
        received_messages.append([message.model_dump() for message in request.messages])
        return "reply", 1, 1

    client = TestClient(build_app(generator=recording_generator, api_key=LLM_API_KEY))
    headers = {"Authorization": f"Bearer {LLM_API_KEY}"}
    histories = [
        [
            {"role": "user", "content": "first request"},
            {"role": "assistant", "content": "first reply"},
        ],
        [{"role": "user", "content": "independent request"}],
    ]

    for messages in histories:
        response = client.post(
            "/v1/chat/completions",
            headers=headers,
            json={"model": "qwen2_5_3b_instruct", "messages": messages},
        )
        assert response.status_code == 200

    assert received_messages == histories
