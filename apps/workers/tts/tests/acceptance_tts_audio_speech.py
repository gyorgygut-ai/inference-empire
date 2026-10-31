import os

import httpx

BASE = os.environ["TTS_AUDIO_SPEECH_API_URL"]
TOKEN = os.environ["GENERATED_TTS_AUDIO_SPEECH_API_KEY"]
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

def main():
    with httpx.Client(timeout=30) as c:
        r = c.get(f"{BASE}/health")
        assert r.status_code == 200

        r = c.post(f"{BASE}/v1/audio/speech", headers={"Authorization":"Bearer bad"}, json={"input":"hi","voice":"a","response_format":"wav"})
        assert r.status_code == 401

        r = c.post(f"{BASE}/v1/audio/speech", headers=HEADERS, json={"input":"hi","voice":"a","response_format":"unknown"})
        assert r.status_code == 422

        r = c.post(f"{BASE}/v1/audio/speech", headers=HEADERS, json={"input":"hi","voice":"a","response_format":"wav"})
        assert r.status_code == 200
        assert len(r.content) > 44, "non-silent wav expected"

if __name__ == "__main__":
    main()
