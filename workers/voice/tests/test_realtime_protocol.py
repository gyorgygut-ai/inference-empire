import pytest

from workers.voice.realtime.protocol import Event


def test_event_json_round_trip():
    ev = Event.session_update({"voice": "bo"})

    out = Event.from_json(ev.to_json())

    assert out.type == "session.update"
    assert out.data == {"session": {"voice": "bo"}}


def test_event_rejects_malformed_json():
    with pytest.raises(ValueError):
        Event.from_json('{"no_type": true}')


def test_session_created_carries_session():
    ev = Event.session_created({"id": "session_1", "voice": "GutAI"})

    assert ev.type == "session.created"
    assert ev.data["session"]["voice"] == "GutAI"


def test_error_event_carries_message():
    ev = Event.error_event("boom")

    assert ev.type == "error"
    assert ev.data["error"]["message"] == "boom"
