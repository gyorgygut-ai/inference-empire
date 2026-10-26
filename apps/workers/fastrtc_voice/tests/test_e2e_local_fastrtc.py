"""Fresh deployed WebRTC exchanges; never accept saved artifacts as test results."""

from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from tests.probe import probe

ARTIFACTS = Path(__file__).parent.parent / "dist" / "proof"


def beam_token() -> str:
    if token := os.getenv("BEAM_TOKEN") or os.getenv("BETA9_TOKEN"):
        return token
    profile = Path.home() / ".beam" / "config.ini"
    if profile.is_file():
        match = re.search(r"^\s*token\s*=\s*(.+)$", profile.read_text(), re.MULTILINE)
        if match:
            return match.group(1).strip()
    raise AssertionError("Set BEAM_TOKEN or configure a Beam profile for deployed E2E proof")


def configured_providers() -> list[str]:
    """Providers with a deployed URL: the probe only proves what is actually deployed."""
    return [p for p in ("modal", "beam") if os.environ.get(f"FASTRTC_{p.upper()}_URL")]


@pytest.fixture(scope="module", params=configured_providers())
def artifact(request: pytest.FixtureRequest) -> dict[str, Any]:
    provider = request.param.upper()
    url = os.environ.get(f"FASTRTC_{provider}_URL")
    assert url, f"Set FASTRTC_{provider}_URL to the deployed worker URL"
    token = beam_token() if provider == "BEAM" else ""
    result = asyncio.run(probe(url, session_s=75.0, bearer_token=token))
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / f"proof-{provider.lower()}-{uuid4().hex}.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    return result


def test_healthz(artifact: dict[str, Any]) -> None:
    assert artifact["healthz"]["status_code"] == 200
    assert artifact["healthz"]["body"] == {"status": "ok", "mode": "proof", "models": []}


def test_rtc_configuration(artifact: dict[str, Any]) -> None:
    config = artifact["rtc_configuration"]
    assert config["status_code"] == 200
    assert config["has_stun"]


def test_offer_answered_and_connected(artifact: dict[str, Any]) -> None:
    session = artifact["session"]
    assert session["offer_status_code"] == 200
    assert session["connected"]
    assert session["connection_state"] in ("connected", "completed")


def test_media_flows_both_ways(artifact: dict[str, Any]) -> None:
    session = artifact["session"]
    assert all(frames > 0 for frames in session["outbound_frames_by_turn"])
    assert all(frames > 0 for frames in session["received_tone_frames_by_turn"])


def test_data_channel_handshake(artifact: dict[str, Any]) -> None:
    assert artifact["session"]["data_channel_open"]


def test_keepalive_lifecycle(artifact: dict[str, Any]) -> None:
    keepalive = artifact["keepalive"]
    assert keepalive["live_status_code"] == 200
    assert keepalive["closed_status_code"] == 404
