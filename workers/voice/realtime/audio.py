"""Audio helper utilities (16-bit PCM / float conversion and resampling).

Kept dependency-light (numpy only) so it can be imported anywhere, including
the test suite, without pulling in torch or the model packages.
"""

from __future__ import annotations

import numpy as np


def pcm16_to_float32(pcm16: bytes) -> np.ndarray:
    """Convert little-endian int16 PCM bytes to float32 in [-1, 1]."""
    if not pcm16:
        return np.zeros(0, dtype=np.float32)
    return np.frombuffer(pcm16, dtype="<i2").astype(np.float32) / 32768.0


def float_to_pcm16(samples: np.ndarray) -> bytes:
    """Convert float audio in [-1, 1] to little-endian int16 PCM bytes."""
    arr = np.asarray(samples, dtype=np.float64)
    clipped = np.clip(arr, -1.0, 1.0)
    return (clipped * 32767.0).astype(np.int16).tobytes()


def _resample(samples: np.ndarray, src_sr: int, dst_sr: int) -> np.ndarray:
    if src_sr == dst_sr or len(samples) == 0:
        return samples
    n = round(len(samples) * dst_sr / src_sr)
    if n == 0:
        return np.zeros(0, dtype=samples.dtype)
    x = np.linspace(0, len(samples) - 1, n)
    return np.interp(x, np.arange(len(samples)), samples)


def resample_pcm16(pcm16: bytes, src_sr: int, dst_sr: int) -> bytes:
    """Resample int16 PCM bytes between sample rates (linear interpolation)."""
    if src_sr == dst_sr:
        return pcm16
    samples = np.frombuffer(pcm16, dtype="<i2").astype(np.float64)
    return _resample(samples, src_sr, dst_sr).astype(np.int16).tobytes()


def resample_float(samples: np.ndarray, src_sr: int, dst_sr: int) -> np.ndarray:
    """Resample float audio between sample rates (linear interpolation)."""
    return _resample(np.asarray(samples, dtype=np.float64), src_sr, dst_sr)
