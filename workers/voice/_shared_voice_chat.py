"""Shared business logic for modal voice chat. No platform imports."""
from __future__ import annotations

import re
import secrets
from typing import Any, Literal, cast

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

    def _load(*args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("weights_only", False)
        return _orig(*args, **kwargs)

    setattr(_load, "_patched", True)
    torch.load = cast(Any, _load)


class VoiceChatInput(BaseModel):
    model_config = ConfigDict(title="VoiceChatInput")
    type: Literal["session.update"]
    session: dict = Field(default_factory=dict)


class RealtimeVoiceInput(BaseModel):
    model_config = ConfigDict(title="RealtimeVoiceInput")
    type: Literal[
        "session.update",
        "input_audio_buffer.append",
        "input_audio_buffer.commit",
        "input_audio_buffer.clear",
    ]
    session: dict | None = Field(default=None)
    audio: str | None = Field(default=None)


class RealtimeVoiceOutput(BaseModel):
    model_config = ConfigDict(title="RealtimeVoiceOutput")
    type: Literal[
        "session.created",
        "session.updated",
        "error",
        "response.audio.delta",
        "response.audio.done",
        "response.text.delta",
        "response.text.done",
        "conversation.item.created",
    ]
    session: dict | None = Field(default=None)
    error: dict | None = Field(default=None)
    delta: str | None = Field(default=None)


def _default_session() -> dict:
    return {
        "id": _rid("sess"),
        "model": "realtime-voice-worker",
        "modalities": ["text", "audio"],
        "instructions": "You are a helpful, concise voice assistant. Respond naturally and briefly.",
        "voice": "GutAI",
        "language": "en",
        "input_audio_format": "pcm16",
        "output_audio_format": "pcm16",
        "input_audio_transcription": {"model": "whisper-1"},
        "turn_detection": {
            "type": "server_vad",
            "threshold": 0.5,
            "silence_duration_ms": 500,
            "prefix_padding_ms": 200,
        },
        "tools": [],
        "tool_choice": "none",
        "temperature": 0.7,
    }


def do_inference(storage, req: RealtimeVoiceInput) -> RealtimeVoiceOutput:
    """Validate at boundary, delegate, return output contract.

    Sync entry point for the realtime session lifecycle: applies a
    `session.update` event to a fresh session and returns the emitted
    `session.updated` event. Audio/utterance turns stay on the realtime
    websocket path (they need the GPU pipeline); session state is pure
    metadata, nothing is written to storage.
    """
    try:
        if req.type != "session.update":
            return RealtimeVoiceOutput(
                type="error",
                error={
                    "message": f"unsupported event type for sync path: {req.type}",
                    "type": "invalid_request_error",
                },
            )
        session = _default_session()
        if req.session:
            session.update(req.session)
        return RealtimeVoiceOutput(type="session.updated", session=session)
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


def load_dependencies():
    """Load all dependencies for realtime voice workers."""
    from workers.services.storage.r2_storage import R2Storage

    return (R2Storage(),)
