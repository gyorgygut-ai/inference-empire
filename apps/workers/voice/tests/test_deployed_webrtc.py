"""Acceptance rows for the deployed workers, asserted from probe artifacts.

Same rows as the local suite, minus the idle row, which the local artifacts
carry. Artifacts come from ``tests/probe.py`` against the deployed URLs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from tests.test_e2e_local_webrtc import (
    TURN_EVENTS,
    _deltas,
    _replies,
    _transcriptions,
)

ARTIFACTS = Path(__file__).parent / "artifacts"

DEPLOYED = {
    "modal": "proof-modal.json",
    "beam-dev": "proof-beam-dev.json",
    "beam": "proof-beam.json",
}


@pytest.fixture(params=sorted(DEPLOYED))
def artifact(request: pytest.FixtureRequest) -> dict[str, Any]:
    path = ARTIFACTS / DEPLOYED[request.param]
    if not path.exists():
        pytest.skip(f"run tests/probe.py first: {path} is missing")
    return json.loads(path.read_text())


def test_healthz(artifact: dict[str, Any]) -> None:
    assert artifact["healthz"]["status_code"] == 200
    assert artifact["healthz"]["body"] == {"status": "ok", "mode": "proof", "models": []}


def test_turn_credentials(artifact: dict[str, Any]) -> None:
    credentials = artifact["turn_credentials"]

    assert credentials["status_code"] == 200
    assert credentials["turn_urls"]
    assert credentials["has_username"] and credentials["has_credential"]


def test_relay_candidate_and_ice_connected(artifact: dict[str, Any]) -> None:
    session = artifact["session_1"]

    assert session["status_code"] == 201
    assert "relay" in session["answer_candidate_types"]
    assert session["ice_connection_state"] == "connected"


def test_turn_emits_exact_event_trace(artifact: dict[str, Any]) -> None:
    events = artifact["session_1"]["events"]

    assert [event["type"] for event in events[:8]] == ["session.created", *TURN_EVENTS]
    assert _transcriptions(events) == ["proof-turn-1", "proof-turn-2"]
    assert _replies(events) == ["proof-reply-1", "proof-reply-2"]
    assert _deltas(events) == ["proof-reply-1", "proof-reply-2"]


def test_received_audio_is_audible(artifact: dict[str, Any]) -> None:
    audio = artifact["session_1"]["audio"]

    assert audio["voiced_seconds"] >= 1.5
    assert audio["rms"] > 0.01


def test_append_over_datachannel_is_rejected(artifact: dict[str, Any]) -> None:
    rejection = artifact["session_1"]["append_rejection"]

    assert rejection["code"] == "invalid_event_for_transport"
    assert rejection["dc_state_after"] == "open"


def test_reconnect_starts_a_fresh_session(artifact: dict[str, Any]) -> None:
    session = artifact["session_2"]

    assert session["ice_connection_state"] == "connected"
    assert session["event_types"] == ["session.created", *TURN_EVENTS]
    assert _transcriptions(session["events"]) == ["proof-turn-1"]
    assert _replies(session["events"]) == ["proof-reply-1"]


def test_malformed_sdp_and_wrong_content_type(artifact: dict[str, Any]) -> None:
    assert artifact["malformed_sdp"]["status_code"] == 400
    assert artifact["wrong_content_type"]["status_code"] == 415
