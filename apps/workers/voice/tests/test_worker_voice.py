from __future__ import annotations

import json

import numpy as np
import pytest
from shared import worker_voice
from dist.contract_voice import Input, Output


def test_contract_requires_audio_and_emits_declared_rate():
    assert Input(audio="c3BlZWNo").sample_rate == 24_000
    assert Output(transcript="hello", response="hi", audio="AA==").sample_rate == 24_000
    with pytest.raises(ValueError):
        Input.model_validate({})


def test_resampling_preserves_signal_shape():
    source = np.ones(240, dtype=np.float32)
    result = worker_voice._resample(source, 24_000, 16_000)
    assert len(result) == 160 and np.allclose(result, 1.0)


def test_reference_voice_manifest_resolves_mounted_wav(tmp_path, monkeypatch):
    voice_path = tmp_path / "gut.wav"
    voice_path.write_bytes(b"non-empty wav fixture")
    manifest_path = tmp_path / "voices.json"
    manifest_path.write_text(
        json.dumps([{"name": "GUT", "path": voice_path.name, "prompt": "Be concise."}]),
        encoding="utf-8",
    )
    monkeypatch.setattr(worker_voice, "REFERENCE_ROOT", tmp_path)
    monkeypatch.setattr(worker_voice, "VOICE_MANIFEST", manifest_path)
    assert worker_voice.available_reference_voices() == {"GUT": voice_path}
    assert worker_voice.resolve_voice("gut") == ("GUT", voice_path)


def test_unknown_voice_falls_back_to_builtin():
    assert worker_voice.resolve_voice("not-a-voice") == ("builtin", None)


def test_non_public_ice_candidates_are_filtered_but_public_candidates_remain():
    sdp = (
        "v=0\r\n"
        "a=candidate:1 1 udp 100 192.168.1.20 5000 typ host\r\n"
        "a=candidate:2 1 udp 90 1.1.1.1 5001 typ srflx\r\n"
    )
    filtered, removed = worker_voice._filter_non_public_ice_candidates(sdp)
    assert removed == 1
    assert "192.168.1.20" not in filtered
    assert "1.1.1.1" in filtered


def test_silent_turn_is_rejected_before_model_load(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(worker_voice, "load_models", lambda: pytest.fail("must not load"))
    with pytest.raises(ValueError, match="empty or silent"):
        worker_voice.run_turn(np.zeros(100, dtype=np.float32), 24_000, "GutAI")
