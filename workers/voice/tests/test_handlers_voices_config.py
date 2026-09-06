import os

from workers.voice.handlers.voices_config import (
    DEFAULT_PERSONA,
    load_voices_config,
    persona_for,
)

VOICES_JSON = os.path.join(
    os.path.dirname(__file__), "..", "voices", "reference_voices", "voices.json"
)


def test_load_voices_config_lists_reference_voices():
    cfg = load_voices_config(VOICES_JSON)

    assert "GutAI" in cfg["voices"]


def test_persona_for_known_voice():
    cfg = load_voices_config(VOICES_JSON)

    out = persona_for(cfg, "GutAI")

    assert isinstance(out, str) and len(out) > 0


def test_persona_falls_back_without_config():
    assert persona_for(None, "GutAI") == DEFAULT_PERSONA
    assert persona_for({}, "GutAI") == DEFAULT_PERSONA
    assert persona_for({"voices": {}}, "nope") == DEFAULT_PERSONA
