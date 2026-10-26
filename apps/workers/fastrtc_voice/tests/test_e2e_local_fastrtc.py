"""Acceptance rows for the local fastrtc proof, asserted from probe artifacts.

Artifacts come from the real entry files:

    modal run worker_fastrtc_voice_modal.py::serve
    uv run --locked python worker_fastrtc_voice_beam.py

then ``tests/probe.py`` writes ``tests/artifacts/proof-local-{modal,beam}.json``.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

ARTIFACTS = Path(__file__).parent / "artifacts"


def load(target: str) -> dict[str, Any]:
    path = ARTIFACTS / f"proof-local-{target}.json"
    if not path.exists():
        pytest.skip(f"run tests/probe.py first: {path} is missing")
    return json.loads(path.read_text())


@pytest.fixture(params=["modal", "beam"])
def artifact(request: pytest.FixtureRequest) -> dict[str, Any]:
    return load(request.param)


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
    assert session["outbound_frames"] > 0
    assert session["inbound_frames"] > 0


def test_data_channel_handshake(artifact: dict[str, Any]) -> None:
    assert artifact["session"]["data_channel_open"]


def test_keepalive_lifecycle(artifact: dict[str, Any]) -> None:
    keepalive = artifact["keepalive"]
    assert keepalive["live_status_code"] == 200
    assert keepalive["closed_status_code"] == 404
