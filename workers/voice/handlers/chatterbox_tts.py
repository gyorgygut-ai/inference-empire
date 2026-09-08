"""Chatterbox zero-shot TTS wrapper.

Loads Chatterbox once and clones a target voice from the committed reference
recordings (``voices/reference_voices/*.wav``). ``generate`` returns 16-bit PCM
at 24 kHz, matching the Realtime client sample rate.

Runs on a GPU container (RTX4090) — Chatterbox is far too slow on CPU.
"""

from __future__ import annotations

import importlib
import os
import threading

import numpy as np

from workers.voice.realtime.audio import float_to_pcm16

REFERENCE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "voices", "reference_voices"
)
TARGET_SR = 24000


class Chatterbox:
    def __init__(
        self,
        reference_dir: str = REFERENCE_DIR,
        model_path: str = "/volumes/models/chatterbox",
        device: str = "cuda",
    ) -> None:
        self.reference_dir = reference_dir
        self.model_path = model_path
        self.device = device
        self.model = None
        self._lock = threading.Lock()

    def load(self) -> Chatterbox:
        try:
            perth = importlib.import_module("perth")
        except ImportError:
            perth = None

        assert perth is not None

        # setuptools >=81 / Python 3.14 dropped pkg_resources, so perth_net's
        # `from pkg_resources import resource_filename` makes
        # PerthImplicitWatermarker resolve to None and from_pretrained() crashes.
        # Fall back to the bundled dummy watermarker (audio is just unwatermarked).
        if getattr(perth, "PerthImplicitWatermarker", None) is None:
            setattr(perth, "PerthImplicitWatermarker", perth.DummyWatermarker)

        try:
            ChatterboxTTS = importlib.import_module("chatterbox.tts").ChatterboxTTS
        except ImportError:
            ChatterboxTTS = None

        assert ChatterboxTTS is not None

        # chatterbox-tts loads its weights from the Hugging Face hub cache and
        # its from_pretrained() takes only ``device`` (no custom local path),
        # so point HF_HOME at the persistent volume (Beam) or local cache dir
        # (run_local) so the download happens once and survives cold starts.
        self.model = ChatterboxTTS.from_pretrained(device=self.device)
        return self

    def voices(self) -> list[str]:
        return sorted(
            os.path.splitext(f)[0]
            for f in os.listdir(self.reference_dir)
            if f.lower().endswith(".wav")
        )

    def _voice_path(self, voice: str) -> str:
        path = os.path.join(self.reference_dir, f"{voice}.wav")
        if not os.path.exists(path):
            raise KeyError(f"unknown voice: {voice}")
        return path

    def generate(
        self,
        text: str,
        voice: str = "GutAI",
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
    ) -> bytes:
        if self.model is None:
            raise RuntimeError("Chatterbox not loaded; call load() first")
        ref = self._voice_path(voice)
        with self._lock:
            wav = self.model.generate(
                text,
                audio_prompt_path=ref,
                exaggeration=exaggeration,
                cfg_weight=cfg_weight,
            )
        arr = np.asarray(wav.squeeze().cpu().numpy(), dtype=np.float32)
        return float_to_pcm16(arr)

    def stream(
        self,
        text: str,
        voice: str = "GutAI",
        cancel=None,
        chunk_size: int = 4096,
    ):
        """Yield 16-bit PCM chunks (24 kHz) for ``text``; stops if ``cancel`` set.

        Used by the assistant worker so TTS audio can be streamed as it is
        produced (Chatterbox itself is non-streaming, so we chunk the full
        clip). Honors an external cancel event for barge-in.
        """
        pcm = self.generate(text, voice=voice)
        for i in range(0, len(pcm), chunk_size):
            if cancel is not None and cancel.is_set():
                break
            yield pcm[i : i + chunk_size]
