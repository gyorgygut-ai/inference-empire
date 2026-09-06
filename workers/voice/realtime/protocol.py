"""OpenAI Realtime API-compatible event protocol (minimal subset).

Implements the inbound/outbound event surface described in PLAN.md §1. Events
are plain JSON objects with a ``type`` field plus arbitrary extra fields. This
module provides (de)serialization and typed constructors so the rest of the
codebase never hand-builds raw JSON dictionaries.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from typing import Any

# Wire sample rates (client <-> server PCM16).
INPUT_SAMPLE_RATE = 24000
OUTPUT_SAMPLE_RATE = 24000


def b64_encode_pcm16(pcm16: bytes) -> str:
    return base64.b64encode(pcm16).decode("ascii")


def b64_decode_pcm16(b64: str) -> bytes:
    return base64.b64decode(b64)


@dataclass
class Event:
    type: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps({"type": self.type, **self.data})

    @classmethod
    def from_json(cls, raw: str) -> Event:
        obj = json.loads(raw)
        if not isinstance(obj, dict) or "type" not in obj:
            raise ValueError(f"not a realtime event: {raw!r}")
        type_ = obj.pop("type")
        return cls(type=type_, data=obj)

    # --- inbound ---------------------------------------------------------
    @classmethod
    def input_audio_append(cls, audio_b64: str, item_id: str | None = None) -> Event:
        d: dict[str, Any] = {"audio": audio_b64}
        if item_id:
            d["item_id"] = item_id
        return cls("input_audio_buffer.append", d)

    @classmethod
    def session_update(cls, session: dict) -> Event:
        return cls("session.update", {"session": session})

    @classmethod
    def conversation_item_create(
        cls, item: dict, previous_item_id: str | None = None
    ) -> Event:
        d: dict[str, Any] = {"item": item}
        if previous_item_id:
            d["previous_item_id"] = previous_item_id
        return cls("conversation.item.create", d)

    @classmethod
    def response_create(cls, response: dict | None = None) -> Event:
        d: dict[str, Any] = {}
        if response:
            d["response"] = response
        return cls("response.create", d)

    @classmethod
    def response_cancel(cls, response_id: str | None = None) -> Event:
        d: dict[str, Any] = {}
        if response_id:
            d["response_id"] = response_id
        return cls("response.cancel", d)

    # --- outbound --------------------------------------------------------
    @classmethod
    def speech_started(
        cls, item_id: str | None = None, audio_start_ms: int | None = None
    ) -> Event:
        d: dict[str, Any] = {}
        if item_id:
            d["item_id"] = item_id
        if audio_start_ms is not None:
            d["audio_start_ms"] = audio_start_ms
        return cls("input_audio_buffer.speech_started", d)

    @classmethod
    def speech_stopped(
        cls, item_id: str | None = None, audio_end_ms: int | None = None
    ) -> Event:
        d: dict[str, Any] = {}
        if item_id:
            d["item_id"] = item_id
        if audio_end_ms is not None:
            d["audio_end_ms"] = audio_end_ms
        return cls("input_audio_buffer.speech_stopped", d)

    @classmethod
    def conversation_item_created(
        cls, item: dict, previous_item_id: str | None = None
    ) -> Event:
        d: dict[str, Any] = {"item": item}
        if previous_item_id:
            d["previous_item_id"] = previous_item_id
        return cls("conversation.item.created", d)

    @classmethod
    def session_created(cls, session: dict) -> Event:
        return cls("session.created", {"session": session})

    @classmethod
    def session_updated(cls, session: dict) -> Event:
        return cls("session.updated", {"session": session})

    @classmethod
    def response_created(cls, response: dict) -> Event:
        return cls("response.created", {"response": response})

    @classmethod
    def response_audio_transcript_delta(
        cls,
        delta: str,
        item_id: str | None = None,
        content_index: int = 0,
        response_id: str | None = None,
    ) -> Event:
        d: dict[str, Any] = {"delta": delta, "content_index": content_index}
        if item_id:
            d["item_id"] = item_id
        if response_id:
            d["response_id"] = response_id
        return cls("response.audio_transcript.delta", d)

    @classmethod
    def response_audio_transcript_done(
        cls,
        transcript: str,
        item_id: str | None = None,
        response_id: str | None = None,
    ) -> Event:
        d: dict[str, Any] = {"transcript": transcript}
        if item_id:
            d["item_id"] = item_id
        if response_id:
            d["response_id"] = response_id
        return cls("response.audio_transcript.done", d)

    @classmethod
    def response_audio_delta(
        cls,
        audio_b64: str,
        item_id: str | None = None,
        content_index: int = 0,
        response_id: str | None = None,
    ) -> Event:
        d: dict[str, Any] = {"delta": audio_b64, "content_index": content_index}
        if item_id:
            d["item_id"] = item_id
        if response_id:
            d["response_id"] = response_id
        return cls("response.audio.delta", d)

    @classmethod
    def response_done(cls, response: dict) -> Event:
        return cls("response.done", {"response": response})

    @classmethod
    def error_event(
        cls,
        message: str,
        error_type: str = "invalid_request_error",
        code: str | None = None,
        event_id: str | None = None,
    ) -> Event:
        error: dict[str, Any] = {"message": message, "type": error_type}
        if code:
            error["code"] = code
        d: dict[str, Any] = {"error": error}
        if event_id:
            d["event_id"] = event_id
        return cls("error", d)
