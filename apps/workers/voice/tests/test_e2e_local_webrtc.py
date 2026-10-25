"""Acceptance rows for the local WebRTC proof, asserted from probe artifacts.

Artifacts come from the real entry files:

    modal run worker_modal_cls_voice.py::serve
    uv run --locked python worker_beam_asgi_voice.py

then ``tests/probe.py`` writes ``tests/artifacts/proof-local-{modal,beam}.json``.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

ARTIFACTS = Path(__file__).parent / "artifacts"

TURN_EVENTS = [
    "input_audio_buffer.speech_started",
    "input_audio_buffer.speech_stopped",
    "conversation.item.input_audio_transcription.completed",
    "response.created",
    "response.output_audio_transcript.delta",
    "response.output_audio_transcript.done",
    "response.done",
]


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


def test_first_turn_emits_exact_event_trace(artifact: dict[str, Any]) -> None:
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


def test_three_minutes_of_silence_keeps_the_call(artifact: dict[str, Any]) -> None:
    session = artifact["session_1"]

    assert session["idle_seconds"] >= 180
    assert session["state_after_idle"] == "connected"
    assert session["event_types"][-len(TURN_EVENTS) :] == TURN_EVENTS


def test_reconnect_starts_a_fresh_session(artifact: dict[str, Any]) -> None:
    session = artifact["session_2"]

    assert session["ice_connection_state"] == "connected"
    assert session["event_types"] == ["session.created", *TURN_EVENTS]
    assert _transcriptions(session["events"]) == ["proof-turn-1"]
    assert _replies(session["events"]) == ["proof-reply-1"]


def test_malformed_sdp_and_wrong_content_type(artifact: dict[str, Any]) -> None:
    assert artifact["malformed_sdp"]["status_code"] == 400
    assert artifact["wrong_content_type"]["status_code"] == 415


def _transcriptions(events: list[dict[str, Any]]) -> list[str]:
    return [
        event["transcript"]
        for event in events
        if event["type"] == "conversation.item.input_audio_transcription.completed"
    ]


def _replies(events: list[dict[str, Any]]) -> list[str]:
    return [
        event["transcript"]
        for event in events
        if event["type"] == "response.output_audio_transcript.done"
    ]


def _deltas(events: list[dict[str, Any]]) -> list[str]:
    return [
        event["delta"]
        for event in events
        if event["type"] == "response.output_audio_transcript.delta"
    ]
