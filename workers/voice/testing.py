"""Voice spec objects + fake builders.

Fake = stub `models` only; the real app + real session logic still run. No
audio handling, no model weights — canned outputs.

Covers openvoice (in-file session logic), chatterbox (in-file REST routes),
modal-chat (in-file session logic). Qwen-beam is deferred to Todo 7: its
session logic lives entirely in the external `realtime` package, so there
is no in-project logic a fake could exercise yet.
"""

import sys
import types
from types import SimpleNamespace

from workers.conftest import WorkerSpec, beam_unwrap


class StubTTS:
    def voices(self):
        return ["GutAI"]

    def generate(self, text, voice="GutAI"):
        return b"\x00\x01" * 8000


class StubConverter:
    def voices(self):
        return ["GutAI"]

    def convert(self, audio24k, voice="GutAI"):
        return b"\x02\x03" * 8000


class StubSileroVAD:
    def load(self):
        return self

    def feed(self, pcm16_16k):
        return {"speech_started": False, "speech_stopped": False}


def _resample_pcm16(pcm: bytes, from_sr: int, to_sr: int) -> bytes:
    import numpy as np

    if from_sr == to_sr:
        return pcm
    arr = np.frombuffer(pcm, dtype="<i2").astype("float32")
    idx = np.linspace(0, len(arr) - 1, max(1, int(len(arr) * to_sr / from_sr)))
    out = np.interp(idx, np.arange(len(arr)), arr).astype("<i2")
    return out.tobytes()


class FakeEvent:
    def __init__(self, type, data=None):
        self.type = type
        self.data = data or {}

    @classmethod
    def from_json(cls, raw):
        import json

        d = json.loads(raw) if isinstance(raw, str) else raw
        obj = cls(d.get("type", ""), {k: v for k, v in d.items() if k != "type"})
        return obj

    def to_json(self):
        import json

        return json.dumps({"type": self.type, **self.data})

    @classmethod
    def error_event(cls, msg):
        return cls("error", {"error": {"message": msg}})

    @classmethod
    def session_created(cls, session):
        return cls("session.created", {"session": session})

    @classmethod
    def session_updated(cls, session):
        return cls("session.updated", {"session": session})

    @classmethod
    def speech_started(cls):
        return cls("input_audio_buffer.speech_started", {})

    @classmethod
    def speech_stopped(cls):
        return cls("input_audio_buffer.speech_stopped", {})

    @classmethod
    def response_created(cls, response):
        return cls("response.created", {"response": response})

    @classmethod
    def response_audio_delta(cls, delta, item_id=None, response_id=None):
        return cls("response.audio.delta", {
            "delta": delta, "item_id": item_id, "response_id": response_id,
        })

    @classmethod
    def response_done(cls, response):
        return cls("response.done", {"response": response})


def _stub_module(name, **attrs):
    mod = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    parent, _, _ = name.rpartition(".")
    if parent:
        pkg = sys.modules.get(parent)
        if pkg is None:
            pkg = types.ModuleType(parent)
            pkg.__path__ = []
            sys.modules[parent] = pkg
        setattr(pkg, name.rpartition(".")[2], mod)
    sys.modules[name] = mod
    return mod


def build_openvoice_app(monkeypatch):
    """Stub converter/VAD/protocol; the in-file OpenVoiceSession runs real."""
    monkeypatch.setitem(sys.modules, "realtime", _realtime_pkg())
    monkeypatch.setitem(sys.modules, "realtime.audio", _mod("realtime.audio", resample_pcm16=_resample_pcm16))
    monkeypatch.setitem(sys.modules, "realtime.protocol", _mod("realtime.protocol", Event=FakeEvent))
    monkeypatch.setitem(sys.modules, "realtime.vad", _mod("realtime.vad", SileroVAD=StubSileroVAD))
    monkeypatch.setitem(sys.modules, "handlers", _handlers_pkg())
    monkeypatch.setitem(
        sys.modules, "handlers.voice_converter",
        _mod("handlers.voice_converter", DEFAULT_VOICE="GutAI", VoiceConverter=StubConverter),
    )
    from workers.voice import worker_beam_asgi_realtime_voice_openvoice as m

    return beam_unwrap(m.worker)(SimpleNamespace(on_start_value=StubConverter()))


def _realtime_pkg():
    pkg = types.ModuleType("realtime")
    pkg.__path__ = []
    return pkg


def _handlers_pkg():
    pkg = types.ModuleType("handlers")
    pkg.__path__ = []
    return pkg


def _mod(name, **attrs):
    return _stub_module(name, **attrs)


def build_chatterbox_app(monkeypatch):
    """Stub tts package; the in-file FastAPI routes run real."""
    monkeypatch.setitem(sys.modules, "handlers", _handlers_pkg())
    monkeypatch.setitem(
        sys.modules, "handlers.chatterbox_tts",
        _mod("handlers.chatterbox_tts", TARGET_SR=24000, Chatterbox=StubTTS),
    )
    from workers.voice import worker_beam_asgi_realtime_voice_chatterbox as m

    return beam_unwrap(m.worker)(SimpleNamespace(on_start_value=StubTTS()))


def build_modal_chat_app(monkeypatch):
    """Stub pipeline; the in-file FastAPI app + RealtimeSession run real."""
    from workers.voice.worker_modal_cls_voice_chat import build_web_app

    pipeline = SimpleNamespace(voices={"GutAI": {}})
    return build_web_app(pipeline)


# Serving shapes resolve to URLs only after deploy; the owner pastes the
# deployed base URL (identity slugs cannot address serving endpoints).
VOICE_OPENVOICE_URL = "owner: paste deployed https URL for voice-openvvoice asgi"
VOICE_CHATTERBOX_URL = "owner: paste deployed https URL for voice-chatterbox asgi"
VOICE_CHAT_URL = "owner: paste deployed https URL for voice-chat-worker web endpoint"


VOICE_OPENVOICE_BEAM_ASGI = WorkerSpec(
    id="voice-openvoice-beam-asgi",
    provider="beam",
    kind="sync",
    shape="beam_asgi",
    module="workers.voice.worker_beam_asgi_realtime_voice_openvoice",
    attr="worker",
    fake_builder=build_openvoice_app,
    extra={"voice_mode": "ws"},
    live_endpoint=VOICE_OPENVOICE_URL,
)

VOICE_CHATTERBOX_BEAM_ASGI = WorkerSpec(
    id="voice-chatterbox-beam-asgi",
    provider="beam",
    kind="sync",
    shape="beam_asgi",
    module="workers.voice.worker_beam_asgi_realtime_voice_chatterbox",
    attr="worker",
    fake_builder=build_chatterbox_app,
    extra={"voice_mode": "rest"},
    live_endpoint=VOICE_CHATTERBOX_URL,
)

VOICE_CHAT_MODAL_ASGI = WorkerSpec(
    id="voice-chat-modal-asgi",
    provider="modal",
    kind="sync",
    shape="modal_asgi",
    module="workers.voice.worker_modal_cls_voice_chat",
    attr="build_web_app",
    fake_builder=build_modal_chat_app,
    extra={"voice_mode": "ws"},
    live_endpoint=VOICE_CHAT_URL,
)
