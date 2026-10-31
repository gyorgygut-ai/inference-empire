import os

import httpx

BASE = os.environ["STT_AUDIO_TRANSCRIPTIONS_API_URL"]
TOKEN = os.environ["GENERATED_STT_AUDIO_TRANSCRIPTIONS_API_KEY"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

def main():
    with httpx.Client(timeout=30) as c:
        r = c.get(f"{BASE}/health")
        assert r.status_code == 200, "health failed"

        r = c.post(f"{BASE}/v1/audio/transcriptions", headers={"Authorization": "Bearer bad"})
        assert r.status_code == 401, "invalid token not rejected"

        r = c.post(f"{BASE}/v1/audio/transcriptions", headers=HEADERS, content=b"")
        assert r.status_code == 422, "empty payload not rejected"

        audio = b"\x52\x49\x46\x46"
        r = c.post(f"{BASE}/v1/audio/transcriptions", headers=HEADERS, content=audio)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data.get("text"), str) and data["text"].strip(), "empty transcript"

if __name__ == "__main__":
    main()
