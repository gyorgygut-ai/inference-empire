import numpy as np

from workers.voice.realtime.audio import (
    float_to_pcm16,
    pcm16_to_float32,
    resample_float,
    resample_pcm16,
)


def test_pcm16_float32_round_trip():
    pcm = np.zeros(4, dtype=np.int16).tobytes()

    out = float_to_pcm16(pcm16_to_float32(pcm))

    assert out == pcm
    assert float_to_pcm16(np.array([1.0], dtype=np.float32)) == np.array(
        [32767], dtype=np.int16
    ).tobytes()


def test_pcm16_empty_stays_empty():
    assert pcm16_to_float32(b"") .size == 0
    assert float_to_pcm16(np.zeros(0)) == b""


def test_resample_pcm16_same_rate_returns_input():
    pcm = np.array([1, 2, 3], dtype=np.int16).tobytes()

    assert resample_pcm16(pcm, 24000, 24000) == pcm


def test_resample_pcm16_downsample_halves_length():
    pcm = np.zeros(2400, dtype=np.int16).tobytes()

    out = resample_pcm16(pcm, 24000, 16000)

    assert len(out) == 1600 * 2


def test_resample_float_upsample_doubles_length():
    samples = np.zeros(100, dtype=np.float64)

    out = resample_float(samples, 16000, 24000)

    assert len(out) == 150
