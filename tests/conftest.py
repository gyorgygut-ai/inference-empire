"""Shared test utilities for unit tests."""

import base64
import importlib
import struct
import zlib
from typing import Any


def _load_worker(module_name: str, class_name: str) -> type:
    """Dynamically load a worker class from a module in the parent directory."""
    mod = importlib.import_module(module_name)
    return getattr(mod, class_name)


def _tiny_png_b64() -> str:
    """Return a base64-encoded 1x1 transparent PNG."""
    sig = b"\x89PNG\r\n\x1a\n"

    def _chunk(ctype: bytes, data: bytes) -> bytes:
        c = ctype + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    raw = b"\x00\x00\x00\x00\x00"
    idat = zlib.compress(raw)
    png = sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")
    return base64.b64encode(png).decode()
