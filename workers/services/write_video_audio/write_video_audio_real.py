from __future__ import annotations

from diffsynth.utils.data.audio_video import write_video_audio as real_write_video_audio


class RealWriteVideoAudio:
    def __call__(self, video, audio, output_path, fps, audio_sample_rate):
        return real_write_video_audio(
            video=video,
            audio=audio,
            output_path=output_path,
            fps=fps,
            audio_sample_rate=audio_sample_rate,
        )
