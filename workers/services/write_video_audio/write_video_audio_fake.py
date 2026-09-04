from __future__ import annotations


class FakeWriteVideoAudio:
    def __init__(self):
        self._calls: list[dict] = []

    def __call__(self, video, audio, output_path, fps, audio_sample_rate):
        self._calls.append({
            "video": video,
            "audio": audio,
            "output_path": output_path,
            "fps": fps,
            "audio_sample_rate": audio_sample_rate,
        })
        with open(output_path, "wb") as f:
            f.write(b"fake_video_bytes")
