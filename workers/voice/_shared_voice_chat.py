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

# Single source of truth for ALL provider image pip deps. Worker files must
# reference these lists, never inline their own pins. One table per distinct
# runtime (voice workers differ by sub-model, not just provider).
# Pre-deploy gate (py3.11 tables): uv run python -c "from workers.voice._shared_voice_chat import <TABLE>; print('\n'.join(<TABLE>))" | uv pip compile --python-version 3.11 -
# QWEN table runs on a python3.10 image: use --python-version 3.10 for it.
REALTIME_IMAGE_PIP_DEPS: list[str] = [
    "torch==2.9.1",
    "transformers==4.57.6",
]
CHATTERBOX_IMAGE_PIP_DEPS: list[str] = [
    "fastapi==0.141.1",
    "uvicorn[standard]==0.52.4",
    "numpy==1.26.4",
    "soundfile==0.14.0",
    "chatterbox-tts==0.1.7",
    "librosa==0.11.0",
]
OPENVOICE_IMAGE_PIP_DEPS: list[str] = [
    "fastapi==0.141.1",
    "uvicorn[standard]==0.52.4",
    "numpy==2.4.6",
    "soundfile==0.14.0",
    "openvoice-cli==0.0.5",
    "librosa==0.9.1",
    "setuptools==84.0.0",
    "torch==2.9.1",
    "torchaudio==2.9.1",
]
# NOTE: chatterbox-tts==0.1.7 dictates torch==2.6.0 / transformers==5.2.0 /
# numpy<2 — the Qwen LLM path moves to transformers 5.x with it. Resolves
# clean; runtime behavior on GPU is unverified (no deploy in this change).
QWEN_IMAGE_PIP_DEPS: list[str] = [
    "fastapi==0.141.1",
    "uvicorn[standard]==0.52.4",
    "numpy==1.26.4",
    "setuptools==84.0.0",
    "soundfile==0.14.0",
    "faster-whisper==1.2.1",
    "ctranslate2==4.4.0",
    "transformers==5.2.0",
    "torch==2.6.0",
    "bitsandbytes==0.50.2",
    "chatterbox-tts==0.1.7",
    "librosa==0.11.0",
    "silero-vad==6.2.1",
    "huggingface-hub[hf-transfer]==1.29.0",
    "hf_xet==1.6.0",
]
CHAT_IMAGE_PIP_DEPS: list[str] = [
    "torch==2.9.1",
    "torchaudio==2.9.1",
    "transformers==4.57.6",
    "accelerate==1.14.0",
    "bitsandbytes==0.50.2",
    "faster-whisper==1.2.1",
    "coqui-tts==0.27.5",
    "soundfile==0.14.0",
    "numpy==2.4.6",
    "fastapi==0.141.1",
    "uvicorn==0.52.4",
    "hf_transfer==0.1.9",
]


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

    _load._patched = True
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
