import base64
import importlib.util
import os

import pytest
from pydantic import ValidationError

APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def _load(name, filename):
    path = os.path.join(APP_DIR, filename)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


shared = _load("rt_shared", "_shared_realtime_voice_qwen.py")
beam_mod = _load("rt_beam", "worker_beam_asgi_realtime_voice_qwen.py")
modal_mod = _load("rt_modal", "worker_modal_cls_realtime_voice_qwen.py")

RealtimeVoiceInput = shared.RealtimeVoiceInput
RealtimeVoiceOutput = shared.RealtimeVoiceOutput


class FakeSTT:
    last_language = "en"

    def transcribe(self, audio24k):
        return "hello world"


class FakeLLM:
    def stream(self, messages, cancel=None):
        yield "Hello"
        yield " world"


class FakeTTS:
    def stream(self, transcript, voice=None, cancel=None):
        assert transcript == "Hello world"
        yield b"\x00\x01" * 160


def _models():
    return {"stt": FakeSTT(), "llm": FakeLLM(), "tts": FakeTTS()}


def _audio_b64():
    pcm = shared.float_to_pcm16(__import__("numpy").zeros(2400, dtype="float32"))
    return base64.b64encode(pcm).decode("ascii")


def test_do_inference_requested_with_right_args():
    req = RealtimeVoiceInput(audio=_audio_b64(), voice="GutAI")
    out = shared.do_inference(_models(), req)
    assert isinstance(out, RealtimeVoiceOutput)
    assert out.transcript == "Hello world"
    assert base64.b64decode(out.audio)


def test_generate_beam_returns_contract():
    out = beam_mod.generate(_models(), audio=_audio_b64(), voice="GutAI")
    assert out["transcript"] == "Hello world"
    assert base64.b64decode(out["audio"])


def test_generate_modal_returns_contract():
    out = modal_mod.generate(_models(), audio=_audio_b64(), voice="GutAI")
    assert out["transcript"] == "Hello world"


def test_generate_rejects_missing_audio():
    with pytest.raises(ValidationError):
        beam_mod.generate(_models(), voice="GutAI")


def test_voice_turn_endpoint_returns_contract():
    from fastapi.testclient import TestClient

    app = shared.build_app(_models())
    with TestClient(app) as client:
        res = client.post("/v1/voice:turn", json={"audio": _audio_b64(), "voice": "GutAI"})
        assert res.status_code == 200
        assert res.json()["transcript"] == "Hello world"


def test_webrtc_handler_roundtrip():
    import numpy as np

    sr, arr = shared.handle_webrtc_audio(_models(), 24000, np.zeros(2400, dtype=np.float32))
    assert sr == 24000
    assert len(arr) > 0


def test_load_dependencies_mocked(monkeypatch):
    models = _models()

    def fake_load():
        return models

    monkeypatch.setattr(beam_mod, "load_dependencies", fake_load)
    assert beam_mod.load_dependencies() is models
    monkeypatch.setattr(modal_mod, "load_dependencies", fake_load)
    assert modal_mod.load_dependencies() is models


class _StubWav:
    def squeeze(self):
        return self

    def cpu(self):
        return self

    def numpy(self):
        import numpy as np

        return np.zeros(2400, dtype=np.float32)


class _StubBuiltinModel:
    def __init__(self):
        self.prompts = []

    def generate(self, text, audio_prompt_path=None):
        self.prompts.append(audio_prompt_path)
        return _StubWav()


def test_tts_empty_dir_uses_builtin_voice(tmp_path):
    assert shared.DEFAULT_VOICE == "gyorgy"
    assert RealtimeVoiceInput(audio=_audio_b64()).voice == "gyorgy"
    tts = shared.ChatterboxTTS(reference_dir=str(tmp_path))
    tts.model = _StubBuiltinModel()
    pcm = tts.generate("hi", voice="gyorgy")
    assert len(pcm) > 0
    assert tts.model.prompts == [None]


def test_tts_unknown_voice_uses_builtin_voice(tmp_path):
    (tmp_path / "gyorgy.wav").write_bytes(b"RIFFstub")
    tts = shared.ChatterboxTTS(reference_dir=str(tmp_path))
    tts.model = _StubBuiltinModel()
    pcm = tts.generate("hi", voice="nope")
    assert len(pcm) > 0
    assert tts.model.prompts == [None]
