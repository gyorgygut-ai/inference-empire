"""OpenVoice ToneColorConverter wrapper — voice-changing (timbre transfer).

Loads the OpenVoice converter checkpoint that ships inside the ``openvoice-cli``
package and precomputes target speaker embeddings (SE) for the committed
reference voices. ``convert`` re-voices an input utterance (the user's captured
speech) into the chosen target voice and returns 16-bit PCM at 24 kHz, ready to
stream back over the Realtime WebSocket.

CPU-only by design (the converter checkpoint is tiny and runs comfortably on a
CPU container — see PLAN.md, OpenVoice worker).
"""

from __future__ import annotations

import importlib
import os
import tempfile
import threading
import wave

import numpy as np

from apps.gpu_workers.voice.realtime.audio import float_to_pcm16, resample_float

REFERENCE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "voices", "reference_voices"
)

DEFAULT_VOICE = "GutAI"
INPUT_SR = 24000
CONVERTER_SR = 16000


def _write_temp_wav(pcm16: bytes, sr: int) -> str:
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm16)
    return path


class VoiceConverter:
    def __init__(
        self,
        reference_dir: str = REFERENCE_DIR,
        device: str = "cpu",
        watermark: bool = False,
    ) -> None:
        self.reference_dir = reference_dir
        self.device = device
        self.watermark = watermark
        self.converter = None
        self.tgt_ses: dict[str, object] = {}
        self._lock = threading.Lock()

    def load(self) -> VoiceConverter:
        try:
            openvoice_cli = importlib.import_module("openvoice_cli")
            ToneColorConverter = importlib.import_module("openvoice_cli.api").ToneColorConverter
        except ImportError:
            openvoice_cli = None
            ToneColorConverter = None

        assert openvoice_cli is not None
        assert ToneColorConverter is not None

        assert openvoice_cli.__file__ is not None
        pkg_dir = os.path.dirname(openvoice_cli.__file__)
        config_path = os.path.join(pkg_dir, "checkpoints", "converter", "config.json")
        ckpt_path = os.path.join(pkg_dir, "checkpoints", "converter", "checkpoint.pth")

        # Subclass to drop the (optional) anti-misuse watermark — it pulls in the
        # `wavmark` package and isn't needed for our use. The base class also
        # rejects `enable_watermark` as a kwarg in this packaged version, so we
        # set `watermark_model = None` ourselves and let `convert` skip it.
        class _Converter(ToneColorConverter):
            def __init__(self, cfg, device="cpu"):
                self.watermark_model = None
                super().__init__(cfg, device=device)

        self.converter = _Converter(config_path, device=self.device)
        self.converter.load_ckpt(ckpt_path)

        # Precompute target SE for every committed reference voice.
        for fname in sorted(os.listdir(self.reference_dir)):
            if fname.lower().endswith(".wav"):
                voice_id = os.path.splitext(fname)[0]
                se = self.converter.extract_se(
                    [os.path.join(self.reference_dir, fname)]
                )
                self.tgt_ses[voice_id] = se
        print(f"[on_start] OpenVoice loaded {len(self.tgt_ses)} reference voices")
        return self

    def voices(self) -> list[str]:
        return sorted(self.tgt_ses.keys())

    def convert(self, pcm16_24k: bytes, target_voice: str) -> bytes:
        """Re-voice ``pcm16_24k`` (client-rate audio) into ``target_voice``.

        Returns 16-bit PCM at 24 kHz.
        """
        if self.converter is None:
            raise RuntimeError("VoiceConverter not loaded; call load() first")
        if target_voice not in self.tgt_ses:
            raise KeyError(f"unknown target voice: {target_voice}")
        tgt_se = self.tgt_ses[target_voice]

        inp_path = _write_temp_wav(pcm16_24k, INPUT_SR)
        try:
            with self._lock:
                src_se = self.converter.extract_se([inp_path])
                audio_16k = self.converter.convert(
                    inp_path, src_se, tgt_se, output_path=None
                )
        finally:
            if os.path.exists(inp_path):
                os.remove(inp_path)

        audio_24k = resample_float(
            np.asarray(audio_16k, dtype=np.float32), CONVERTER_SR, INPUT_SR
        )
        return float_to_pcm16(audio_24k)
