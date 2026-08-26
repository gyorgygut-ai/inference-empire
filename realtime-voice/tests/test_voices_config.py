"""Tests for the reference-voice config loader (no GPU / no models)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from handlers.voices_config import (
    DEFAULT_PERSONA,
    load_voices_config,
    persona_for,
)

CFG = {
    "default_voice": "GutAI",
    "voices": {
        "GutAI": {"file": "GutAI.wav", "persona": "P-GutAI"},
        "ff": {"file": "ff.wav", "persona": "P-ff"},
    },
}


def test_load_voices_config_roundtrip():
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(CFG, f)
        path = f.name
    try:
        loaded = load_voices_config(path)
        assert loaded["default_voice"] == "GutAI"
        assert loaded["voices"]["ff"]["persona"] == "P-ff"
    finally:
        Path(path).unlink()


def test_persona_for_known_and_unknown():
    assert persona_for(CFG, "ff") == "P-ff"
    assert persona_for(CFG, "GutAI") == "P-GutAI"
    # unknown voice -> falls back to the default voice's persona
    assert persona_for(CFG, "nope") == "P-GutAI"
    # no config at all -> default persona
    assert persona_for(None, "ff") == DEFAULT_PERSONA
