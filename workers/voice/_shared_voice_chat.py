"""Shared business logic for modal voice chat. No platform imports."""
from __future__ import annotations

import re
import secrets
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

SAMPLE_RATE_IN = 16000
TTS_SR = 24000
MAX_NEW_TOKENS = 384
# Voice/language options advertised to the UI (source of truth = this worker).
SUPPORTED_LANGUAGES = {"en": "English", "hu": "Hungarian"}

_SENT_RE = re.compile(r"[.!?]+(?=\s|$)")


def find_sentence_end(text: str) -> int:
    """Return index just after the last sentence-ending punctuation in `text`."""
    matches = list(_SENT_RE.finditer(text))
    if not matches:
        return -1
    return matches[-1].end()


def pcm_float_to_int16(wav: np.ndarray) -> bytes:
    wav = np.asarray(wav, dtype=np.float32)
    clipped = np.clip(wav, -1.0, 1.0) * 32767.0
    return clipped.astype(np.int16).tobytes()


def resample_int16(audio_int16: np.ndarray, from_sr: int, to_sr: int) -> np.ndarray:
    """Resample int16 PCM using torch (no torchaudio dependency)."""
    import torch
    import torch.nn.functional as F

    t = torch.tensor(audio_int16.astype(np.float32) / 32768.0).unsqueeze(0).unsqueeze(0)
    out = F.interpolate(t, scale_factor=to_sr / from_sr, mode="linear", align_corners=False)
    return out.squeeze().numpy().astype(np.float32)


def _rid(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


def _patch_torch_load():
    """Revert torch.load to pre-2.6 default (weights_only=False).

    TTS 0.22.0 pickles custom config classes (XttsConfig, etc.) and calls
    torch.load without overriding the default, which torch>=2.6 changed to
    weights_only=True and rejects. Only TTS in this stack uses the pickle
    path (transformers uses safetensors, whisper uses CTranslate2), so this
    is scoped to the TTS load and avoids downgrading torch globally.
    """
    import torch

    if getattr(torch.load, "_patched", False):
        return
    _orig = torch.load

    def _load(*args, **kwargs):
        kwargs.setdefault("weights_only", False)
        return _orig(*args, **kwargs)

    _load._patched = True
    torch.load = _load


class VoiceChatInput(BaseModel):
    model_config = ConfigDict(title="VoiceChatInput")
    type: Literal["session.update"]
    session: dict = Field(default_factory=dict)
