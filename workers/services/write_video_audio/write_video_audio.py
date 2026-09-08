from __future__ import annotations

from typing import Protocol


class WriteVideoAudio(Protocol):
    """Callable that writes video and audio to a file.

    Signature: (video, audio, output_path, fps, audio_sample_rate) -> None
    """

    def __call__(self, video, audio, output_path, fps, audio_sample_rate) -> None: ...
