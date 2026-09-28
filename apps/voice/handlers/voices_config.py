"""Reference-voice configuration: maps a selected voice id to its speaker
audio file and its LLM persona (system prompt).

This is the single source of truth for "per selected reference voice"
behavior in the assistant worker (worker 1): the chosen voice drives both the
TTS timbre (via the reference wav) and the assistant's persona.

`collect_voices.py` scaffolds this file (only if absent) so human-authored
personas are never clobbered.
"""

from __future__ import annotations

import json

DEFAULT_PERSONA = (
    "You are a helpful, concise voice assistant. Keep replies short and "
    "conversational; avoid long monologues."
)


def load_voices_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def persona_for(cfg: dict | None, voice: str | None, default_voice: str = "GutAI") -> str:
    """Return the system-prompt persona for ``voice`` (falls back gracefully)."""
    if not cfg:
        return DEFAULT_PERSONA
    voices = cfg.get("voices", {})
    entry = voices.get(voice) or voices.get(default_voice) or {}
    return entry.get("persona") or DEFAULT_PERSONA
