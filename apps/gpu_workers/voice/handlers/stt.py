"""Speech-to-text handler: faster-whisper loaded from a volume path.

The model is loaded once (in ``on_start``) and ``transcribe`` is called per
turn. A lock serializes GPU access so multiple concurrent sessions sharing
the same model object don't race (PLAN.md §6).
"""

from __future__ import annotations

import threading

import numpy as np

from apps.gpu_workers.voice.realtime.audio import resample_pcm16

WHISPER_INPUT_SR = 24000
WHISPER_SR = 16000


class WhisperSTT:
    def __init__(
        self,
        model_path: str,
        device: str = "cuda",
        compute_type: str = "int8",
    ) -> None:
        self.model_path = model_path
        self.device = device
        self.compute_type = compute_type
        self.model = None
        self.last_language: str | None = None
        self._lock = threading.Lock()

    def load(self) -> WhisperSTT:
        from faster_whisper import WhisperModel

        self.model = WhisperModel(self.model_path, device=self.device, compute_type=self.compute_type)
        return self

    def transcribe(self, pcm16_24k: bytes, language: str | None = None) -> str:
        if self.model is None:
            raise RuntimeError("STT not loaded; call load() first")
        pcm16_16k = resample_pcm16(pcm16_24k, WHISPER_INPUT_SR, WHISPER_SR)
        audio = np.frombuffer(pcm16_16k, dtype="<i2").astype(np.float32) / 32768.0
        with self._lock:
            segments, info = self.model.transcribe(audio, language=language, beam_size=5)
            self.last_language = getattr(info, "language", None)
            text = "".join(seg.text for seg in segments).strip()
        return text
