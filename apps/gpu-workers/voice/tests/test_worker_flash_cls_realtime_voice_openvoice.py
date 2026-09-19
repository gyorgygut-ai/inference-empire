import pytest
from pydantic import ValidationError

import apps.gpu_workers.voice.worker_flash_cls_realtime_voice_openvoice as worker_mod


def test_generate_session_update_returns_updated_event():
    out = worker_mod.generate(
        None, type="session.update", session={"voice": "Bob"}
    )
    assert out["type"] == "session.updated"
    assert out["session"]["voice"] == "Bob"
    assert out["session"]["id"]


def test_generate_audio_event_returns_error():
    out = worker_mod.generate(
        None, type="input_audio_buffer.append", audio="AAAA"
    )
    assert out["type"] == "error"
    assert out["error"]["type"] == "invalid_request_error"


def test_generate_rejects_missing_type():
    with pytest.raises(ValidationError):
        worker_mod.generate(None)