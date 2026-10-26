"""Route contract of the fastrtc worker app: in process, no media, no network."""
from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from shared import worker_fastrtc_voice
from shared.worker_fastrtc_voice import STUN_SERVER, build_app


class _FakeMintResponse:
    """Stand-in for the HF TURN mint response (HTTP side effect stubbed)."""

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {"iceServers": [{"urls": "turn:turn.example.com:3478", "username": "u", "credential": "c"}]}


class _FakeAsyncClient:
    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    async def get(self, *args: object, **kwargs: object) -> _FakeMintResponse:
        return _FakeMintResponse()


@pytest.fixture
def client() -> TestClient:
    return TestClient(build_app())


def test_healthz_reports_proof_mode(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mode": "proof", "models": []}


def test_rtc_configuration_stun_only_without_hf_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("HF_TOKEN", raising=False)

    response = client.get("/rtc-configuration")

    assert response.status_code == 200
    assert response.json() == {"iceServers": [dict(STUN_SERVER)]}


def test_rtc_configuration_mints_turn_with_hf_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HF_TOKEN", "test-token")
    monkeypatch.setattr(worker_fastrtc_voice.httpx, "AsyncClient", _FakeAsyncClient)

    response = client.get("/rtc-configuration")

    assert response.status_code == 200
    servers = response.json()["iceServers"]
    assert servers[0] == dict(STUN_SERVER)
    assert any(s["urls"].startswith("turn:") for s in servers)


def test_keepalive_unknown_connection_404(client: TestClient) -> None:
    response = client.get("/keepalive/no-such-connection")

    assert response.status_code == 404
    assert response.json() == {"error": "unknown_connection"}


def test_webrtc_offer_route_mounted(client: TestClient) -> None:
    paths = {route.path for route in client.app.routes}

    assert "/webrtc/offer" in paths
