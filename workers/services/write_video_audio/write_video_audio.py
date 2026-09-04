from __future__ import annotations

from collections.abc import Callable
from typing import Any


class WriteVideoAudio(Callable[..., Any]):
    """Callable that writes video and audio to a file.

    Signature: (video, audio, output_path, fps, audio_sample_rate) -> None
    """
