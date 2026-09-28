from __future__ import annotations

from typing import Any


class FakeVideoPipe:
    """Source fake: respond with exactly these frames + audio when requested."""

    audio_vae: Any = None

    def __init__(self, frames, audio):
        self._frames = frames
        self._audio = audio

    def __call__(self, **kwargs):
        return self._frames, self._audio
