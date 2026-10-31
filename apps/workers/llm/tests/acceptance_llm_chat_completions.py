import os

import httpx

BASE = os.environ["LLM_CHAT_COMPLETIONS_API_URL"]
TOKEN = os.environ["GENERATED_LLM_CHAT_COMPLETIONS_API_KEY"]
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

def main():
    with httpx.Client(timeout=30) as c:
        r = c.get(f"{BASE}/health")
        assert r.status_code == 200

        r = c.post(f"{BASE}/v1/chat/completions", headers={"Authorization": "Bearer bad"}, json={"model":"x","messages":[]})
        assert r.status_code == 401

        r = c.post(f"{BASE}/v1/chat/completions", headers=HEADERS, json={"model":"x"})
        assert r.status_code == 422

        payload = {"model":"test","messages":[{"role":"user","content":"hi"}]}
        r = c.post(f"{BASE}/v1/chat/completions", headers=HEADERS, json=payload)
        assert r.status_code == 200
        data = r.json()
        content = data.get("choices",[{}])[0].get("message",{}).get("content","")
        assert isinstance(content,str) and content.strip(), "empty completion"

if __name__ == "__main__":
    main()
