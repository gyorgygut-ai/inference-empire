import os

import httpx

BASE = os.environ.get("VOICE_REALTIME_SESSION_API_URL")
if not BASE:
    raise RuntimeError("VOICE_REALTIME_SESSION_API_URL not set")
SERVER_TOKEN = os.environ["GENERATED_VOICE_WORKER_AUTH_TOKEN"]
HEADERS_SERVER = {"Authorization": f"Bearer {SERVER_TOKEN}"}

def main():
    with httpx.Client(timeout=30) as c:
        r = c.post(f"{BASE}/v1/realtime/client_secrets", headers={"Authorization":"Bearer bad"})
        assert r.status_code == 401, "bad server token not rejected"

        r = c.post(f"{BASE}/v1/realtime/calls", headers={"Authorization":"Bearer expired"})
        assert r.status_code == 401, "bad session token not rejected"

        r = c.post(f"{BASE}/v1/realtime/client_secrets", headers=HEADERS_SERVER)
        assert r.status_code == 200
        data = r.json()
        assert "value" in data and "expires_at" in data and "rtc_configuration" in data

        assert True

if __name__ == "__main__":
    main()
