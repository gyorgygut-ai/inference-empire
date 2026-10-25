"""Route contract of the voice worker app, in process, no media."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from shared.worker_voice import build_app

ENV_FILE = Path(__file__).resolve().parents[4] / ".env"


@pytest.fixture
def client() -> TestClient:
    return TestClient(build_app())


def test_healthz_reports_proof_mode(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mode": "proof", "models": []}


def test_turn_credentials_without_hf_token_names_it(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("HF_TOKEN", raising=False)

    response = client.get("/turn-credentials")

    assert response.status_code == 503
    assert "HF_TOKEN" in response.json()["error"]


def test_turn_credentials_minted_from_existing_hf_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    token = dotenv_values(ENV_FILE).get("HF_TOKEN")
    if not token:
        pytest.skip("no HF_TOKEN in the workspace .env")
    monkeypatch.setenv("HF_TOKEN", token)

    response = client.get("/turn-credentials")

    assert response.status_code == 200
    servers = response.json()["iceServers"]
    assert any("turn:" in url for entry in servers for url in _urls(entry))
    assert any(entry.get("username") and entry.get("credential") for entry in servers)


def test_rejects_non_sdp_content_type(client: TestClient) -> None:
    response = client.post("/v1/realtime/calls", json={})

    assert response.status_code == 415


def test_rejects_malformed_sdp(client: TestClient) -> None:
    response = client.post(
        "/v1/realtime/calls",
        content=b"v=0\n",
        headers={"Content-Type": "application/sdp"},
    )

    assert response.status_code == 400


def _urls(entry: dict[str, Any]) -> list[str]:
    urls = entry.get("urls")
    if isinstance(urls, str):
        return [urls]
    return [str(url) for url in urls] if urls else []
