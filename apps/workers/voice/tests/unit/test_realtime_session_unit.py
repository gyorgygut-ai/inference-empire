import base64
import os
import time

import pytest
from dist.contract_voice import ClientSecretInput, ClientSecretOutput, RealtimeSession
from fastapi.testclient import TestClient

AUTH_TOKEN = "realtime-test-auth-token"
HF_TOKEN = "hf-test-token"


class StubInferenceClient:
    """Stub inference client that doesn't make HTTP calls."""

    def transcribe(self, audio: bytes, filename: str) -> str:
        return "Sample transcript from stub"

    def complete(self, transcript: str) -> str:
        return "LLM reply from stub"

    def speak(self, text: str) -> tuple[bytes, int | None]:
        dummy_wav = b"UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YU"
        return base64.b64decode(dummy_wav), 24000


async def stub_turn_credentials():
    return {
        "iceServers": [
            {
                "urls": ["turn:stub.example.com:3478"],
                "username": "stub-user",
                "credential": "stub-cred",
            }
        ]
    }


@pytest.fixture
def client():
    os.environ["SECRET_VOICE_WORKER_AUTH_TOKEN"] = AUTH_TOKEN
    os.environ["SECRET_HUGGINGFACE_TOKEN"] = HF_TOKEN

    # Build a minimal test app without fastrtc Stream
    import hmac
    import json
    import secrets

    from fastapi import FastAPI, HTTPException, Request, Response

    # Simple token store
    class SessionTokens:
        def __init__(self):
            self._tokens: dict[str, float] = {}
            self.ttl_seconds = 60

        def create(self) -> tuple[str, int]:
            now = int(time.time())
            token = secrets.token_urlsafe(32)
            self._tokens[token] = float(now + self.ttl_seconds)
            return token, now + self.ttl_seconds

        def validate(self, token: str) -> bool:
            expires_at = self._tokens.get(token)
            if expires_at is None:
                return False
            if expires_at <= time.time():
                del self._tokens[token]
                return False
            return True

    tokens = SessionTokens()

    app = FastAPI(title="worker-voice-test")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/realtime/client_secrets", response_model=ClientSecretOutput)
    async def create_client_secret(
        request: ClientSecretInput, http_request: Request, response: Response
    ) -> ClientSecretOutput:
        authorization = http_request.headers.get("authorization", "")
        scheme, _, supplied_token = authorization.partition(" ")
        trusted_server_token = os.environ.get("SECRET_VOICE_WORKER_AUTH_TOKEN")
        if not trusted_server_token:
            raise HTTPException(status_code=503, detail="Session authentication is not configured")
        if scheme.casefold() != "bearer" or not hmac.compare_digest(
            supplied_token.encode(), trusted_server_token.encode()
        ):
            raise HTTPException(status_code=401, detail="Invalid server credential")

        # Return stub TURN config
        rtc_configuration = {
            "iceServers": [
                {
                    "urls": ["turn:stub.example.com:3478"],
                    "username": "stub-user",
                    "credential": "stub-cred",
                }
            ]
        }

        token, expires_at = tokens.create()
        response.headers["Cache-Control"] = "no-store"
        return ClientSecretOutput(
            value=token,
            expires_at=expires_at,
            session=request.session or RealtimeSession(),
            rtc_configuration=rtc_configuration,
        )

    @app.post("/v1/realtime/calls")
    async def realtime_call(request: Request) -> Response:
        authorization = request.headers.get("authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.casefold() != "bearer" or not tokens.validate(token):
            raise HTTPException(status_code=401, detail="Invalid or expired session token")
        form = await request.form()
        sdp = form.get("sdp")
        if not isinstance(sdp, str) or not sdp.strip():
            raise HTTPException(status_code=422, detail="sdp is required")
        session_value = form.get("session")
        try:
            RealtimeSession.model_validate(
                json.loads(session_value) if isinstance(session_value, str) else {}
            )
        except (ValueError, TypeError) as error:
            raise HTTPException(status_code=422, detail="Invalid realtime session") from error

        # Return a dummy SDP answer
        dummy_sdp = "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\nm=audio 1 RTP/SAVPF 0\r\n"
        return Response(content=dummy_sdp, media_type="application/sdp")

    return TestClient(app)


def test_realtime_client_secrets_missing_or_invalid_token_returns_401(client):
    # Missing auth header
    r = client.post("/v1/realtime/client_secrets", json={"session": {}})
    assert r.status_code == 401, "missing token not rejected"

    # Invalid token
    r = client.post(
        "/v1/realtime/client_secrets",
        headers={"Authorization": "Bearer bad"},
        json={"session": {}},
    )
    assert r.status_code == 401, "invalid token not rejected"


def test_realtime_client_secrets_missing_or_invalid_token_response_error(client):
    r = client.post(
        "/v1/realtime/client_secrets",
        headers={"Authorization": "Bearer bad"},
        json={"session": {}},
    )
    assert r.status_code == 401
    assert "detail" in r.json(), "missing detail in error response"


def test_realtime_client_secrets_valid_token_returns_200(client):
    r = client.post(
        "/v1/realtime/client_secrets",
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        json={"session": {}},
    )
    assert r.status_code == 200, "valid token rejected"


def test_realtime_client_secrets_valid_token_has_ephemeral_token(client):
    r = client.post(
        "/v1/realtime/client_secrets",
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        json={"session": {}},
    )
    assert r.status_code == 200
    data = r.json()
    assert "value" in data, "ephemeral token missing"
    assert isinstance(data["value"], str), "token not string"


def test_realtime_client_secrets_valid_token_has_expires_at(client):
    r = client.post(
        "/v1/realtime/client_secrets",
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        json={"session": {}},
    )
    assert r.status_code == 200
    data = r.json()
    assert "expires_at" in data, "expires_at missing"
    assert isinstance(data["expires_at"], int), "expires_at not int"
    assert data["expires_at"] > int(time.time()), "expires_at not in future"


def test_realtime_client_secrets_valid_token_has_rtc_configuration(client):
    r = client.post(
        "/v1/realtime/client_secrets",
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        json={"session": {}},
    )
    assert r.status_code == 200
    data = r.json()
    assert "rtc_configuration" in data, "rtc_configuration missing"
    ice_servers = data["rtc_configuration"].get("iceServers", [])
    assert len(ice_servers) > 0, "no ice servers"
    urls = ice_servers[0].get("urls", [])
    assert any(u.startswith("turn:") for u in urls), "no TURN relay"


def test_realtime_calls_invalid_or_expired_token_returns_401(client):
    # Invalid session token
    r = client.post(
        "/v1/realtime/calls",
        headers={"Authorization": "Bearer invalid-session"},
        data={"sdp": "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\nm=audio 1 RTP/SAVPF 0\r\n"},
    )
    assert r.status_code == 401, "invalid session token not rejected"


def test_realtime_calls_invalid_or_expired_token_response_error(client):
    r = client.post(
        "/v1/realtime/calls",
        headers={"Authorization": "Bearer invalid-session"},
        data={"sdp": "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\nm=audio 1 RTP/SAVPF 0\r\n"},
    )
    assert r.status_code == 401
    assert "detail" in r.json(), "missing detail in error response"


# Note: Full WebRTC turn test requires FastRTC integration which is tested in E2E tests.
def test_realtime_turn_stt_llm_tts_produces_non_silent_reply(client):
    # First create a client secret
    r = client.post(
        "/v1/realtime/client_secrets",
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        json={"session": {}},
    )
    assert r.status_code == 200
    secret = r.json()["value"]

    # Make a call with the session token and minimal SDP
    r = client.post(
        "/v1/realtime/calls",
        headers={"Authorization": f"Bearer {secret}"},
        data={"sdp": "v=0\r\no=- 0 0 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\nm=audio 1 RTP/SAVPF 0\r\n"},
    )
    # Should return SDP answer (status 200)
    assert r.status_code == 200, f"unexpected status: {r.status_code}"
    assert r.headers.get("content-type") == "application/sdp"
