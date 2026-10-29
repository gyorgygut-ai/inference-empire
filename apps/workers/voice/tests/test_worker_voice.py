from __future__ import annotations

import numpy as np
import pytest
from shared import worker_voice
from shared.contract_voice import Input, Output


def test_contract_requires_audio_and_emits_declared_rate():
    assert Input(audio="c3BlZWNo").sample_rate == 24_000
    assert Output(transcript="hello", response="hi", audio="AA==").sample_rate == 24_000
    with pytest.raises(ValueError):
        Input.model_validate({})


def test_resampling_preserves_signal_shape():
    source = np.ones(240, dtype=np.float32)
    result = worker_voice._resample(source, 24_000, 16_000)
    assert len(result) == 160 and np.allclose(result, 1.0)


def test_reference_assets_seed_to_the_persistent_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(worker_voice, "REFERENCE_ROOT", tmp_path)
    hashes = worker_voice.verify_and_seed_voices()
    manifest = worker_voice.voice_manifest()["voices"]
    assert set(manifest) == {"GutAI", "bo", "bp", "ff", "sa"}
    assert hashes == worker_voice.verify_and_seed_voices()
    assert all((tmp_path / item["file"]).is_file() for item in manifest.values())


def test_unknown_voice_fails_closed():
    with pytest.raises(ValueError, match="unknown voice ID"):
        worker_voice.validate_voice("not-a-voice")


def test_silent_turn_is_rejected_before_model_load(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(worker_voice, "load_models", lambda: pytest.fail("must not load"))
    with pytest.raises(ValueError, match="empty or silent"):
        worker_voice.run_turn(np.zeros(100, dtype=np.float32), 24_000, "GutAI")
