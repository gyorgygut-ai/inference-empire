import re

import numpy as np
import pytest

from workers.voice._shared_voice_chat import (
    _rid,
    find_sentence_end,
    pcm_float_to_int16,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hello world.", 12),
        ("Hello. World", 6),
        ("Wait... what? Yes!", 18),
        ("No punctuation", -1),
        ("", -1),
    ],
)
def test_find_sentence_end(text, expected):
    end = find_sentence_end(text)

    assert end == expected


def test_pcm_float_to_int16_round_trip():
    wav = np.array([0.0, 1.0, -1.0, 0.5], dtype=np.float32)

    out = pcm_float_to_int16(wav)

    assert out == np.array([0, 32767, -32767, 16383], dtype=np.int16).tobytes()


def test_rid_unique():
    first = _rid("sess")

    second = _rid("sess")

    assert first != second


def test_rid_format():
    rid = _rid("sess")

    assert re.fullmatch(r"sess_[0-9a-f]{12}", rid) is not None
