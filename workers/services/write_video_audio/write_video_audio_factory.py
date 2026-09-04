from __future__ import annotations

import os

from workers.services.write_video_audio.write_video_audio_fake import FakeWriteVideoAudio
from workers.services.write_video_audio.write_video_audio_real import RealWriteVideoAudio


def write_video_audio_factory(target: str | None = None) -> RealWriteVideoAudio | FakeWriteVideoAudio:
    if target is None:
        target = os.environ.get("WRITE_VIDEO_AUDIO_TARGET", "real")
    if target == "fake":
        return FakeWriteVideoAudio()
    if target == "real":
        return RealWriteVideoAudio()
    raise ValueError(f"unknown write_video_audio target: {target!r}")
