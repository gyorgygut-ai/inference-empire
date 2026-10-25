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


shared = _load("rt_shared", "shared/worker_realtime_voice.py")
beam_mod = _load("rt_beam", "worker_beam_asgi_realtime_voice_qwen.py")
modal_mod = _load("rt_modal", "worker_modal_cls_realtime_voice_qwen.py")
flash_mod = _load("rt_flash", "worker_flash_cls_realtime_voice_qwen.py")

RealtimeVoiceInput = shared.RealtimeVoiceInput
RealtimeVoiceOutput = shared.RealtimeVoiceOutput


class FakeSTT:
    last_language = "en"

    def transcribe(self, audio24k):
        _ = audio24k
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
    req = RealtimeVoiceInput(audio=_audio_b64(), voice="test-voice")
    out = shared.do_inference(_models(), req)
    assert isinstance(out, RealtimeVoiceOutput)
    assert out.transcript == "Hello world"
    assert base64.b64decode(out.audio)


def test_generate_beam_returns_contract():
    out = beam_mod.generate(_models(), audio=_audio_b64(), voice="test-voice")
    assert out["transcript"] == "Hello world"
    assert base64.b64decode(out["audio"])


def test_generate_modal_returns_contract():
    out = modal_mod.generate(_models(), audio=_audio_b64(), voice="test-voice")
    assert out["transcript"] == "Hello world"


def test_generate_flash_returns_contract():
    out = flash_mod.generate(_models(), audio=_audio_b64(), voice="test-voice")
    assert out["transcript"] == "Hello world"
    assert base64.b64decode(out["audio"])


def test_generate_flash_rejects_missing_audio():
    with pytest.raises(ValidationError):
        flash_mod.generate(_models(), voice="test-voice")


def test_generate_webrtc_flash_roundtrip():
    import numpy as np

    sr, arr = flash_mod.generate_webrtc(_models(), 24000, np.zeros(2400, dtype=np.float32))
    assert sr == 24000
    assert len(arr) > 0


def test_generate_rejects_missing_audio():
    with pytest.raises(ValidationError):
        beam_mod.generate(_models(), voice="test-voice")


def test_voice_turn_endpoint_returns_contract():
    from fastapi.testclient import TestClient

    app = shared.build_app(_models())
    with TestClient(app) as client:
        res = client.post("/v1/voice:turn", json={"audio": _audio_b64(), "voice": "test-voice"})
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
    monkeypatch.setattr(flash_mod, "load_dependencies", fake_load)
    assert flash_mod.load_dependencies() is models


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


def test_voice_required():
    with pytest.raises(ValidationError):
        RealtimeVoiceInput(audio=_audio_b64())


def test_tts_empty_dir_uses_builtin_voice(tmp_path):
    tts = shared.ChatterboxTTS(reference_dir=str(tmp_path))
    tts.model = _StubBuiltinModel()
    pcm = tts.generate("hi", voice="test-voice")
    assert len(pcm) > 0
    assert tts.model.prompts == [None]


def test_tts_unknown_voice_uses_builtin_voice(tmp_path):
    (tmp_path / "test-voice.wav").write_bytes(b"RIFFstub")
    tts = shared.ChatterboxTTS(reference_dir=str(tmp_path))
    tts.model = _StubBuiltinModel()
    pcm = tts.generate("hi", voice="unknown-voice")
    assert len(pcm) > 0
    assert tts.model.prompts == [None]


class _StubCaptureModel:
    """Stub LLM backend: captures generate() kwargs, emits one token."""

    def __init__(self, device="cpu"):
        import torch

        self.device = device
        self.seen_kwargs: dict = {}
        self._torch = torch

    def generate(self, **kwargs):
        self.seen_kwargs = kwargs
        kwargs["streamer"].put(kwargs["input_ids"][:, :1])
        kwargs["streamer"].end()


def _stub_tokenizer(input_ids):
    class _StubTokenizer:
        def apply_chat_template(self, messages, add_generation_prompt=True, return_tensors="pt"):
            _ = (messages, add_generation_prompt)
            assert return_tensors == "pt"
            return {"input_ids": input_ids}

    return _StubTokenizer()


def test_qwen_stream_passes_tensor_input_ids():
    import torch

    ids = torch.zeros(1, 5, dtype=torch.long)
    llm = shared.QwenLLM.__new__(shared.QwenLLM)
    import threading

    llm._lock = threading.Lock()
    llm.model = _StubCaptureModel()
    llm.tokenizer = _stub_tokenizer(ids)
    llm.max_new_tokens = 8
    assert list(llm.stream([{"role": "user", "content": "hi"}])) is not None
    seen = llm.model.seen_kwargs
    assert isinstance(seen["input_ids"], torch.Tensor)
    assert seen["input_ids"].ndim == 2
    assert "inputs" not in seen


def test_qwen_stream_unblocks_when_generate_dies():
    import threading
    import time

    import torch

    class _DyingModel(_StubCaptureModel):
        def generate(self, **kwargs):
            raise RuntimeError("boom")

    llm = shared.QwenLLM.__new__(shared.QwenLLM)
    llm._lock = threading.Lock()
    llm.model = _DyingModel()
    llm.tokenizer = _stub_tokenizer(torch.zeros(1, 5, dtype=torch.long))
    llm.max_new_tokens = 8
    out = []
    t0 = time.time()
    thread = threading.Thread(
        target=lambda: out.append(list(llm.stream([{"role": "user", "content": "hi"}])))
    )
    thread.start()
    thread.join(timeout=30)
    assert not thread.is_alive(), "stream hung after generate thread died"
    assert len(out) == 1 and all(tok == "" for tok in out[0]), f"unexpected tokens: {out}"
    assert time.time() - t0 < 30
