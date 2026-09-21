"""Silero VAD wrapper for streaming turn-boundary detection.

CPU-only. The model is loaded once and fed fixed 512-sample (16 kHz) windows;
we apply a single-sample probability threshold plus a short silence hold to
mark speech start/stop. This is intentionally simple — tune the threshold and
hold against real network audio (PLAN.md §9).
"""

from __future__ import annotations

import importlib
import threading

import numpy as np

from apps.gpu_workers.voice.realtime.audio import pcm16_to_float32

WINDOW_SAMPLES = 512  # Silero expects 512 samples @ 16 kHz
SAMPLE_RATE = 16000
DEFAULT_THRESHOLD = 0.5
DEFAULT_SPEECH_HOLD_S = 0.3  # silence before we declare speech stopped


class SileroVAD:
    def __init__(
        self,
        threshold: float = DEFAULT_THRESHOLD,
        speech_hold_s: float = DEFAULT_SPEECH_HOLD_S,
    ) -> None:
        self.threshold = threshold
        self.speech_hold_s = speech_hold_s
        self._model = None
        self._lock = threading.Lock()
        self._reset()

    def load(self) -> SileroVAD:
        try:
            load_silero_vad = importlib.import_module("silero_vad").load_silero_vad
        except ImportError:
            load_silero_vad = None

        assert load_silero_vad is not None
        self._model = load_silero_vad()
        return self

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def _reset(self) -> None:
        self._buf = np.zeros(0, dtype=np.float32)
        self._silent_samples = 0
        self._in_speech = False

    def reset(self) -> None:
        self._reset()

    def feed(self, pcm16_16k: bytes) -> dict:
        """Feed 16-bit PCM @16 kHz; return a status delta.

        Returns ``{"speech_started": bool, "speech_stopped": bool}`` where
        ``speech_started`` is True exactly once when voice begins and
        ``speech_stopped`` is True exactly once after ``speech_hold_s`` of
        silence.
        """
        if self._model is None:
            raise RuntimeError("VAD not loaded; call load() first")

        audio = pcm16_to_float32(pcm16_16k)
        self._buf = np.concatenate([self._buf, audio])

        started = False
        stopped = False
        with self._lock:
            while len(self._buf) >= WINDOW_SAMPLES:
                window = self._buf[:WINDOW_SAMPLES]
                self._buf = self._buf[WINDOW_SAMPLES:]
                prob = self._model(_torch(window), SAMPLE_RATE).item()
                if prob >= self.threshold:
                    self._silent_samples = 0
                    if not self._in_speech:
                        self._in_speech = True
                        started = True
                else:
                    self._silent_samples += WINDOW_SAMPLES
                    if self._in_speech and self._silent_samples >= int(
                        self.speech_hold_s * SAMPLE_RATE
                    ):
                        self._in_speech = False
                        stopped = True
        return {"speech_started": started, "speech_stopped": stopped}


def _torch(window: np.ndarray):
    import torch

    return torch.from_numpy(window).unsqueeze(0)
