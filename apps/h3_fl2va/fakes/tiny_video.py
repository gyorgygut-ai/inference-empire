"""Tiny video loader: real ByteDance/AnimateDiff-Lightning inference on tiny-sd.

TinyVideoPipe mirrors the production pipe call shape: pipe(**kwargs) ->
(video, audio) with video as float tensor (1, F, C, H, W). AnimateDiff emits
no audio, so audio is None and audio_vae only carries the sample rate.

write_video_audio() is the ffmpeg fallback: it muxes frames to a real mp4
(silent-track via anullsrc when audio is None) so the artifact check stays
real without diffsynth. Pass it as the write_video_audio dep; generate()
needs no change.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace

BASE_ID = "segmind/tiny-sd"
MODEL_ID = "ByteDance/AnimateDiff-Lightning"
NUM_FRAMES = 16
STEPS = 4
SIZE = 256
SAMPLE_RATE = 24000


def load_tiny_video_pipe():
    """Boot AnimateDiff-Lightning on tiny-sd. import torch in function body."""
    import torch
    from diffusers import AnimateDiffPipeline, LCMScheduler, MotionAdapter

    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    adapter = MotionAdapter.from_pretrained(MODEL_ID, torch_dtype=dtype)
    pipe = AnimateDiffPipeline.from_pretrained(
        BASE_ID, motion_adapter=adapter, torch_dtype=dtype
    )
    pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)
    if torch.cuda.is_available():
        pipe = pipe.to("cuda")
    return TinyVideoPipe(pipe)


class TinyVideoPipe:
    """Real pipe with the production call shape. keyframes are dropped:
    the Lightning module is text-to-video only."""

    def __init__(self, pipe):
        self._pipe = pipe
        self.audio_vae = SimpleNamespace(sample_rate=SAMPLE_RATE)

    def __call__(self, **kwargs):
        import torch

        generator = None
        if kwargs.get("seed") is not None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            generator = torch.Generator(device=device).manual_seed(kwargs["seed"])
        out = self._pipe(
            prompt=kwargs["prompt"],
            height=kwargs.get("height") or SIZE,
            width=kwargs.get("width") or SIZE,
            num_frames=kwargs.get("num_frames") or NUM_FRAMES,
            num_inference_steps=kwargs.get("num_inference_steps") or STEPS,
            generator=generator,
        )
        frames = out.frames[0]
        video = torch.stack(
            [torch.from_numpy(__import__("numpy").array(f.convert("RGB"))).permute(2, 0, 1)
             for f in frames]
        ).unsqueeze(0).float() / 255.0
        return video, None


def _to_pil_list(video):
    import numpy as np
    from PIL import Image

    if isinstance(video, list):
        return [f.convert("RGB") if isinstance(f, Image.Image) else Image.fromarray(f) for f in video]
    if hasattr(video, "detach"):
        video = video.detach().cpu()
        if video.ndim == 5:
            video = video[0]
        if video.shape[0] <= 4 and video.ndim == 4:
            video = video.permute(1, 2, 3, 0) if video.shape[0] == 3 else video.permute(0, 2, 3, 1)
        arr = (video.numpy() * 255).clip(0, 255).astype("uint8") if video.max() <= 1.5 else video.numpy().astype("uint8")
        return [Image.fromarray(frame) for frame in arr]
    arr = np.asarray(video)
    if arr.ndim == 5:
        arr = arr[0]
    if arr.max() <= 1.5:
        arr = (arr * 255).clip(0, 255).astype("uint8")
    return [Image.fromarray(frame) for frame in arr]


def write_video_audio(video, audio, output_path, fps, audio_sample_rate):
    """ffmpeg fallback writer: real mp4 out, silent track when audio is None."""
    import wave

    frames = _to_pil_list(video)
    with tempfile.TemporaryDirectory() as tmp:
        for i, frame in enumerate(frames):
            frame.save(Path(tmp) / f"frame_{i:04d}.png")
        cmd = ["ffmpeg", "-y", "-framerate", str(fps),
               "-i", str(Path(tmp) / "frame_%04d.png")]
        if audio is None:
            cmd += ["-f", "lavfi", "-i",
                    f"anullsrc=r={audio_sample_rate}:cl=mono"]
        else:
            wav = str(Path(tmp) / "audio.wav")
            with wave.open(wav, "wb") as fh:
                fh.setnchannels(1)
                fh.setsampwidth(2)
                fh.setframerate(audio_sample_rate)
                fh.writeframes((__import__("numpy").asarray(audio) * 32767).astype("<i2").tobytes())
            cmd += ["-i", wav]
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                "-shortest", str(output_path)]
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    return output_path
