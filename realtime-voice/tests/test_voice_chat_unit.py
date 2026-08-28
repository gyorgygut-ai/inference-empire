import asyncio
import base64
import threading
from types import SimpleNamespace

import pytest

numpy = pytest.importorskip("numpy")
np = numpy

import worker_modal_cls_voice_chat as w  # noqa: E402


# --------------------------------------------------------------------------
# Pure helpers
# --------------------------------------------------------------------------
def test_find_sentence_end_basic():
    assert w.find_sentence_end("Hello. How are you") == 6
    assert w.find_sentence_end("Hi there") == -1
    assert w.find_sentence_end("Done!") == 5
    assert w.find_sentence_end("A? B. C!") == 8


def test_pcm_float_to_int16():
    out = w.pcm_float_to_int16(np.array([0.0, 1.0, -1.0], dtype=np.float32))
    assert isinstance(out, bytes)
    assert np.frombuffer(out, dtype=np.int16).tolist() == [0, 32767, -32767]


def test_module_exports():
    assert w.app is not None
    assert w.image is not None
