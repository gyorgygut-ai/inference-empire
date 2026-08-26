"""Unit tests for the Realtime event protocol (de)serialization."""

from __future__ import annotations

import base64

import pytest

from realtime.protocol import Event


def test_roundtrip_inbound_audio():
    raw = base64.b64encode(b"\x00\x01\x02\x03").decode("ascii")
    ev = Event.input_audio_append(raw, item_id="it_1")
    assert ev.type == "input_audio_buffer.append"
    assert ev.data["item_id"] == "it_1"
    back = Event.from_json(ev.to_json())
    assert back.type == ev.type
    assert back.data == ev.data


def test_roundtrip_session_update():
    ev = Event.session_update({"instructions": "be brief"})
    back = Event.from_json(ev.to_json())
    assert back.data["session"]["instructions"] == "be brief"


@pytest.mark.parametrize(
    "factory,key",
    [
        (lambda: Event.response_create(), "response.create"),
        (lambda: Event.response_cancel("r1"), "response.cancel"),
        (lambda: Event.speech_started(item_id="i1"), "input_audio_buffer.speech_started"),
        (lambda: Event.speech_stopped(item_id="i1"), "input_audio_buffer.speech_stopped"),
        (lambda: Event.response_audio_transcript_delta("hi", item_id="i1"), "response.audio_transcript.delta"),
        (lambda: Event.response_audio_transcript_done("hi", item_id="i1"), "response.audio_transcript.done"),
        (lambda: Event.response_audio_delta("AAAA", item_id="i1"), "response.audio.delta"),
        (lambda: Event.conversation_item_created({"type": "message"}), "conversation.item.created"),
        (lambda: Event.response_created({"id": "r"}), "response.created"),
        (lambda: Event.response_done({"id": "r"}), "response.done"),
        (lambda: Event.error_event("boom"), "error"),
    ],
)
def test_roundtrip_outbound(factory, key):
    ev = factory()
    assert ev.type == key
    back = Event.from_json(ev.to_json())
    assert back.type == key
    assert back.data == ev.data


def test_invalid_event_raises():
    with pytest.raises(ValueError):
        Event.from_json('{"foo": 1}')
    with pytest.raises(ValueError):
        Event.from_json("not json")
