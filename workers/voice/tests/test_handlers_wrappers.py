import numpy as np
import pytest

from workers.voice.handlers.chatterbox_tts import TARGET_SR, Chatterbox
from workers.voice.handlers.llm import QwenLLM
from workers.voice.handlers.stt import WhisperSTT
from workers.voice.handlers.voice_converter import VoiceConverter
from workers.voice.realtime.vad import SileroVAD


class _Segment:
    def __init__(self, text):
        self.text = text


class _Info:
    def __init__(self, language):
        self.language = language


class FakeWhisperModel:
    def __init__(self, text=" hello ", language="en"):
        self.text = text
        self.language = language
        self.seen = None

    def transcribe(self, audio, language=None, beam_size=5):
        self.seen = (audio, language, beam_size)
        return [_Segment(self.text)], _Info(self.language)


class _Tensor:
    def __init__(self, arr):
        self._arr = arr

    def squeeze(self):
        return self

    def cpu(self):
        return self

    def numpy(self):
        return self._arr


class FakeChatterboxModel:
    def __init__(self):
        self.seen = None

    def generate(self, text, audio_prompt_path=None, exaggeration=0.5, cfg_weight=0.5):
        self.seen = (text, audio_prompt_path, exaggeration, cfg_weight)
        return _Tensor(np.zeros(TARGET_SR, dtype=np.float32))


class _Prob:
    def __init__(self, value):
        self._value = value

    def item(self):
        return self._value


def test_stt_refuses_unloaded_model():
    with pytest.raises(RuntimeError):
        WhisperSTT("/nope").transcribe(b"\x00\x00")


def test_stt_returns_stripped_transcript_and_language():
    stt = WhisperSTT("/nope")
    stt.model = FakeWhisperModel()

    out = stt.transcribe(np.zeros(2400, dtype=np.int16).tobytes())

    assert out == "hello"
    assert stt.last_language == "en"


def test_llm_refuses_unloaded_model():
    with pytest.raises(RuntimeError):
        next(QwenLLM("/nope").stream([{"role": "user", "content": "hi"}]))


def test_chatterbox_refuses_unloaded_model():
    with pytest.raises(RuntimeError):
        Chatterbox().generate("hi")


def test_chatterbox_lists_reference_voices():
    out = Chatterbox().voices()

    assert {"bo", "bp", "ff", "GutAI", "sa"} <= set(out)


def test_chatterbox_rejects_unknown_voice():
    tts = Chatterbox()
    tts.model = FakeChatterboxModel()

    with pytest.raises(KeyError):
        tts.generate("hi", voice="nope")


def test_chatterbox_returns_24k_pcm16():
    tts = Chatterbox()
    tts.model = FakeChatterboxModel()

    out = tts.generate("hi", voice="GutAI")

    assert out == np.zeros(TARGET_SR, dtype=np.int16).tobytes()


def test_converter_refuses_unloaded_model():
    with pytest.raises(RuntimeError):
        VoiceConverter().convert(b"\x00\x00", "GutAI")


def test_converter_rejects_unknown_voice():
    converter = VoiceConverter()
    converter.converter = object()

    with pytest.raises(KeyError):
        converter.convert(b"\x00\x00", "nope")


def test_vad_refuses_unloaded_model():
    with pytest.raises(RuntimeError):
        SileroVAD().feed(b"\x00\x00")


def test_vad_reports_speech_start_once(monkeypatch):
    import workers.voice.realtime.vad as vad_mod

    vad = SileroVAD(speech_hold_s=0.0)
    vad._model = lambda window, sr: _Prob(0.9)
    monkeypatch.setattr(vad_mod, "_torch", lambda window: window)

    first = vad.feed(np.zeros(512, dtype=np.int16).tobytes())
    second = vad.feed(np.zeros(512, dtype=np.int16).tobytes())

    assert first == {"speech_started": True, "speech_stopped": False}
    assert second == {"speech_started": False, "speech_stopped": False}
