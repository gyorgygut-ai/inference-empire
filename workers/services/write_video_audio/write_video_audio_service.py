from __future__ import annotations


class WriteVideoAudioService:
    def __call__(self, video, audio, output_path, fps, audio_sample_rate):
        from diffsynth.utils.data.audio_video import write_video_audio as diffsynth_write

        return diffsynth_write(
            video=video,
            audio=audio,
            output_path=output_path,
            fps=fps,
            audio_sample_rate=audio_sample_rate,
        )
