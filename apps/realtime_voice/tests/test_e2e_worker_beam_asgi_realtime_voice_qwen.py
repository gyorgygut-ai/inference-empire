"""E2E tests for realtime-voice workers (Beam ASGI + Modal ASGI).

Run worker/provider tests with: uv run --locked pytest apps/realtime_voice/tests/test_e2e_worker_beam_asgi_realtime_voice_qwen.py -k "e2e"
"""
from __future__ import annotations

import base64
import importlib.util
import os
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.realtime_voice._shared_realtime_voice_qwen import (
    RealtimeVoiceInput,
    RealtimeVoiceOutput,
    float_to_pcm16,
)

APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def _load(name: str, filename: str) -> Any:
    path = os.path.join(APP_DIR, filename)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


shared = _load("rt_shared", "_shared_realtime_voice_qwen.py")


def _load_beam() -> Any:
    """Load beam worker module with provider SDKs stubbed at module scope.

    `worker_beam_asgi_realtime_voice_qwen.py` imports `beam` and builds
    `Image(...)`, `Volume(...)`, `QueueDepthAutoscaler(...)`, and the
    `@asgi(...)` decorator at module level, so it cannot be imported without
    the `beam` package. We exec the file with lightweight stubs in place so
    `generate(...)` is still importable for contract checks.
    """
    path = os.path.join(APP_DIR, "worker_beam_asgi_realtime_voice_qwen.py")
    src = open(path, encoding="utf-8").read()

    stubbed_src = src.replace(
        "from beam import Image, QueueDepthAutoscaler, Volume, asgi",
        "",
        1,
    )

    ns: dict[str, object] = {
        "__name__": "rt_beam_guarded",
        "Image": _ImageFactory(),
        "Volume": _VolumeFactory(),
        "QueueDepthAutoscaler": _QueueDepthAutoscalerFactory(),
        "asgi": _asgi_decorator_stub,
        "_ImagePlaceholder": _ImagePlaceholder,
        "_VolumeStub": _VolumeStub,
        "_QueueDepthAutoscalerStub": _QueueDepthAutoscalerStub,
    }
    exec(compile(stubbed_src, path, "exec"), ns)

    import types

    mod = types.ModuleType("rt_beam_guarded")
    mod.__dict__.update(ns)
    return mod


class _ImageFactory:
    """Callable placeholder that returns a chainable image stub."""

    def __call__(self, *args, **kwargs):
        return _ImagePlaceholder()


class _ImagePlaceholder:
    def add_commands(self, cmds):
        return self

    def add_python_packages(self, pkgs):
        return self

    def with_envs(self, envs):
        return self


class _VolumeFactory:
    """Callable placeholder for beam.Volume(...) at module scope."""

    def __call__(self, *args, **kwargs):
        return _VolumeStub()


class _VolumeStub:
    def __init__(self, *args, **kwargs):
        self.name = None
        self.mount_path = None


class _QueueDepthAutoscalerFactory:
    """Callable placeholder for beam.QueueDepthAutoscaler(...) at module scope."""

    def __call__(self, *args, **kwargs):
        return _QueueDepthAutoscalerStub()


class _QueueDepthAutoscalerStub:
    def __init__(self, *args, **kwargs):
        self.max_containers = None
        self.min_containers = None


def _asgi_decorator_stub(*args, **kwargs):
    def _wrap(fn):
        return fn

    return _wrap


def _load_modal() -> Any:
    return _load("rt_modal", "worker_modal_cls_realtime_voice_qwen.py")


# ---------------------------------------------------------------------------
# Fake providers for DI-based contract tests
# ---------------------------------------------------------------------------


class FakeSTT:
    last_language = "en"

    def transcribe(self, audio24k: bytes) -> str:
        return "hello world"


class FakeLLM:
    def stream(self, messages: list[dict], cancel: object = None):
        yield "Hello"
        yield " world"


class FakeTTS:
    def stream(self, transcript: str, voice: str | None = None, cancel: object = None):
        assert transcript == "Hello world"
        yield b"\x00\x01" * 160


def _models() -> dict[str, Any]:
    return {"stt": FakeSTT(), "llm": FakeLLM(), "tts": FakeTTS()}


def _audio_b64() -> str:
    pcm = float_to_pcm16(np.zeros(2400, dtype="float32"))
    return base64.b64encode(pcm).decode("ascii")


# ---------------------------------------------------------------------------
# Contract-shape tests (run without -k "e2e")
# ---------------------------------------------------------------------------


def test_realtime_voice_input_contract_shape():
    """RealtimeVoiceInput should be constructible from contract fields."""
    inp = RealtimeVoiceInput(audio=_audio_b64(), voice="test-voice")
    assert inp.audio
    assert inp.voice == "test-voice"
    assert inp.sample_rate == 24000
    assert inp.language == "en"


def test_realtime_voice_output_contract_shape():
    """RealtimeVoiceOutput should validate the contract output shape."""
    out = RealtimeVoiceOutput(
        audio=base64.b64encode(b"\x00\x01" * 80).decode("ascii"),
        transcript="hello",
        sample_rate=24000,
    )
    assert out.audio
    assert out.transcript == "hello"
    assert out.sample_rate == 24000


def test_voice_field_required_on_input_contract():
    """Voice is a contract-required field."""
    with pytest.raises(ValidationError):
        RealtimeVoiceInput(audio=_audio_b64())


def test_audio_field_required_on_input_contract():
    """Audio is a contract-required field."""
    with pytest.raises(ValidationError):
        RealtimeVoiceInput(voice="test-voice")


def test_transcript_field_required_on_output_contract():
    """Transcript is a contract-required field on output."""
    with pytest.raises(ValidationError):
        RealtimeVoiceOutput(
            audio=base64.b64encode(b"\x00" * 80).decode("ascii"),
            sample_rate=24000,
        )


def test_audio_field_required_on_output_contract():
    """Audio is a contract-required field on output."""
    with pytest.raises(ValidationError):
        RealtimeVoiceOutput(transcript="hello", sample_rate=24000)


def test_sample_rate_defaults_on_output_contract():
    """Sample rate defaults to 24000 when omitted on output."""
    out = RealtimeVoiceOutput(
        audio=base64.b64encode(b"\x00\x01" * 80).decode("ascii"),
        transcript="hello",
    )
    assert out.sample_rate == 24000


# ---------------------------------------------------------------------------
# E2E tests (selected by -k "e2e")
# ---------------------------------------------------------------------------


def test_contract_post_voice_turn_returns_contract():
    """Contract POST /v1/voice:turn should return 200 + contract output."""
    app = shared.build_app(_models())
    with TestClient(app) as client:
        res = client.post(
            "/v1/voice:turn",
            json={"audio": _audio_b64(), "voice": "test-voice"},
        )
        assert res.status_code == 200
        out = res.json()
        assert out["transcript"] == "Hello world"
        assert base64.b64decode(out["audio"])
        assert out["sample_rate"] == 24000
        RealtimeVoiceOutput(**out)


def test_health_endpoint_ok():
    """GET / should return ok status."""
    app = shared.build_app(_models())
    with TestClient(app) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"


def test_beam_worker_generate_returns_contract():
    """Beam worker generate() should return contract-shaped output."""
    beam_mod = _load_beam()
    out = beam_mod.generate(_models(), audio=_audio_b64(), voice="test-voice")
    assert isinstance(out, dict)
    assert out["transcript"]
    assert base64.b64decode(out["audio"])
    assert out["sample_rate"] == 24000
    RealtimeVoiceOutput(**out)


def test_modal_worker_generate_returns_contract():
    """Modal worker generate() should return contract-shaped output."""
    modal_mod = _load_modal()
    out = modal_mod.generate(_models(), audio=_audio_b64(), voice="test-voice")
    assert isinstance(out, dict)
    assert out["transcript"] == "Hello world"
    assert base64.b64decode(out["audio"])
    RealtimeVoiceOutput(**out)


def test_beam_worker_rejects_missing_audio():
    """Beam generate() should reject missing audio per contract."""
    beam_mod = _load_beam()
    with pytest.raises(ValidationError):
        beam_mod.generate(_models(), voice="test-voice")


def test_modal_worker_rejects_missing_audio():
    """Modal generate() should reject missing audio per contract."""
    modal_mod = _load_modal()
    with pytest.raises(ValidationError):
        modal_mod.generate(_models(), voice="test-voice")


def test_webrtc_handler_roundtrip():
    """handle_webrtc_audio should return (24000, non-empty ndarray)."""
    sr, arr = shared.handle_webrtc_audio(
        _models(), 24000, np.zeros(2400, dtype=np.float32)
    )
    assert sr == 24000
    assert len(arr) > 0
