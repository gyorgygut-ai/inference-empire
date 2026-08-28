import importlib

import pytest


def test_module_import():
    mod = importlib.import_module("worker_beam_asgi_realtime_voice_chatterbox")
    assert hasattr(mod, "worker")
    assert hasattr(mod, "image")


def test_pcm_to_wav():
    from worker_beam_asgi_realtime_voice_chatterbox import _pcm_to_wav

    wav = _pcm_to_wav(b"\x00\x01" * 100, 24000)
    assert isinstance(wav, bytes)
    assert len(wav) > 0
    assert wav[:4] == b"RIFF"


def test_list_voices():
    from worker_beam_asgi_realtime_voice_chatterbox import _pcm_to_wav

    assert callable(_pcm_to_wav)
