import asyncio
from types import SimpleNamespace

import numpy as np
import pytest
from pydantic import ValidationError

import workers.voice.worker_modal_cls_voice_chat as worker_mod
from workers.voice._shared_voice_chat import find_sentence_end, pcm_float_to_int16
from workers.voice.worker_modal_cls_voice_chat import RealtimeSession


def _fake_pipeline():
    return SimpleNamespace(voices={})


def test_generate_session_update_returns_updated_event():
    out = worker_mod.generate(
        _fake_pipeline(), type="session.update", session={"voice": "Bob"}
    )
    assert out["type"] == "session.updated"
    assert out["session"]["voice"] == "Bob"
    assert out["session"]["id"]


def test_generate_rejects_missing_type():
    with pytest.raises(ValidationError):
        worker_mod.generate(_fake_pipeline())


def test_generate_wraps_internal_errors():
    with pytest.raises(RuntimeError, match="inference failed"):
        worker_mod.generate(SimpleNamespace(voices=None), type="session.update")


def test_realtime_session_on_connect_emits_session_created():
    session = RealtimeSession(_fake_pipeline())
    events = []

    async def send(event: dict):
        events.append(event)

    session.send = send
    asyncio.run(session.on_connect())
    types = [e["type"] for e in events]
    assert "session.created" in types
    assert "conversation.created" in types


def test_find_sentence_end():
    assert find_sentence_end("Hello world. Next.") == 18
    assert find_sentence_end("no punctuation") == -1


def test_pcm_float_to_int16():
    out = pcm_float_to_int16(np.array([0.0, 1.0, -1.0], dtype=np.float32))
    assert out == np.array([0, 32767, -32767], dtype=np.int16).tobytes()