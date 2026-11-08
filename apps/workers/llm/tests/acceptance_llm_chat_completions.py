import os

import httpx

BASE = os.environ["LLM_CHAT_COMPLETIONS_API_URL"].rstrip("/")
TOKEN = os.environ["LLM_CHAT_COMPLETIONS_API_KEY"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def main():
    with httpx.Client(timeout=300) as client:
        response = client.post(
            f"{BASE}/v1/chat/completions",
            headers=HEADERS,
            json={
                "model": "qwen2_5_3b_instruct",
                "messages": [{"role": "user", "content": "Reply with a short greeting."}],
            },
        )
        assert response.status_code == 200, "valid request failed"
        content = response.json()["choices"][0]["message"]["content"]
        assert isinstance(content, str) and content.strip(), "empty completion"


if __name__ == "__main__":
    main()
