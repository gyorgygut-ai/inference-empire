from __future__ import annotations


class FakeWriteVideoAudio:
    def __init__(self, payload: bytes):
        self._payload = payload

    def __call__(self, video, audio, output_path, fps, audio_sample_rate):
        with open(output_path, "wb") as f:
            f.write(self._payload)
