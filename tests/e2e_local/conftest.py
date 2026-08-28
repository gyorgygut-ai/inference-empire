"""Shared test utilities for e2e-local tests."""

import base64
import importlib
import io
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

WORKERS: dict[str, dict[str, Any]] = {
    "small_vision": {
        "module": "worker_flash_cls_small_vision",
        "class": "Qwen2VLVisionWorker",
        "deps": ["torch", "transformers"],
        "pip_deps": ["torch", "transformers"],
    },
    "flux2_klein9b": {
        "module": "worker_flash_cls_flux2_klein9b",
        "class": "FluxKleinWorker",
        "deps": ["torch", "transformers", "diffsynth"],
        "pip_deps": ["torch", "transformers"],
    },
    "minimax_h3_ref2va": {
        "module": "worker_flash_cls_minimax_h3_ref2va",
        "class": "MiniMaxH3Ref2VAWorker",
        "deps": ["torch", "transformers", "diffsynth"],
        "pip_deps": ["torch", "transformers"],
    },
    "minimax_h3_fl2va": {
        "module": "worker_flash_cls_minimax_h3_fl2va",
        "class": "MiniMaxH3Fl2VAWorker",
        "deps": ["torch", "transformers", "diffsynth"],
        "pip_deps": ["torch", "transformers"],
    },
    "krea2_ref2img": {
        "module": "worker_flash_cls_krea2_ref2img",
        "class": "Krea2Ref2ImgWorker",
        "deps": ["torch", "transformers"],
        "pip_deps": ["torch", "transformers"],
    },
    "minimax_h3_fl2va_beam_tq": {
        "module": "worker_beam_tq_minimax_h3_fl2va",
        "class": "MiniMaxH3Fl2VAWorker",
        "deps": ["torch", "transformers", "diffsynth"],
        "pip_deps": ["torch", "transformers"],
    },
    "minimax_h3_ref2va_beam_tq": {
        "module": "worker_beam_tq_minimax_h3_ref2va",
        "class": "MiniMaxH3Ref2VAWorker",
        "deps": ["torch", "transformers", "diffsynth"],
        "pip_deps": ["torch", "transformers"],
    },
    "minimax_h3_ref2va_comfy_beam_tq": {
        "module": "worker_beam_tq_minimax_h3_ref2va_comfy",
        "class": "ValidatedInput",
        "deps": ["torch"],
        "pip_deps": ["torch"],
    },
    "minimax_h3_fl2va_modal": {
        "module": "worker_modal_cls_minimax_h3_fl2va",
        "class": "MiniMaxH3Fl2VAWorker",
        "deps": ["torch", "transformers", "diffsynth"],
        "pip_deps": ["torch", "transformers"],
    },
    "minimax_h3_ref2va_modal": {
        "module": "worker_modal_cls_minimax_h3_ref2va",
        "class": "MiniMaxH3Ref2VAWorker",
        "deps": ["torch", "transformers", "diffsynth"],
        "pip_deps": ["torch", "transformers"],
    },
    "voice_chatterbox": {
        "module": "worker_beam_asgi_realtime_voice_chatterbox",
        "class": "worker",
        "deps": ["fastapi"],
        "pip_deps": ["fastapi"],
    },
    "voice_openvoice": {
        "module": "worker_beam_asgi_realtime_voice_openvoice",
        "class": "worker",
        "deps": ["fastapi"],
        "pip_deps": ["fastapi"],
    },
    "voice_qwen": {
        "module": "worker_beam_asgi_realtime_voice_qwen",
        "class": "worker",
        "deps": ["fastapi"],
        "pip_deps": ["fastapi"],
    },
}


def _load_worker(module_name: str, class_name: str) -> type:
    """Dynamically load a worker class from a module in the parent directory."""
    mod = importlib.import_module(module_name)
    return getattr(mod, class_name)


def _tiny_png_b64() -> str:
    """Return a base64-encoded 1x1 transparent PNG."""
    import struct
    import zlib

    sig = b"\x89PNG\r\n\x1a\n"

    def _chunk(ctype: bytes, data: bytes) -> bytes:
        c = ctype + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    raw = b"\x00\x00\x00\x00\x00"
    idat = zlib.compress(raw)
    png = sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")
    return base64.b64encode(png).decode()


def build_worker(name: str) -> Any:
    """Build a worker instance for testing."""
    cfg = WORKERS.get(name, {})
    module_name = cfg.get("module", f"worker_{name}")
    class_name = cfg.get("class", f"{name.title().replace('_', '')}Worker")
    cls = _load_worker(module_name, class_name)
    return cls()


def check_deps(name: str) -> list[str]:
    """Check if worker dependencies can be imported. Returns list of failed imports."""
    cfg = WORKERS.get(name, {})
    deps = cfg.get("deps", [])
    failed = []
    for dep in deps:
        try:
            importlib.import_module(dep)
        except ImportError:
            failed.append(dep)
    return failed


def check_pip(name: str) -> list[str]:
    """Check pip-installed packages. Returns list of missing packages."""
    cfg = WORKERS.get(name, {})
    pip_deps = cfg.get("pip_deps", [])
    failed = []
    for dep in pip_deps:
        try:
            importlib.import_module(dep)
        except ImportError:
            failed.append(dep)
    return failed


def validate_output(output: Any, schema: type[BaseModel]) -> None:
    """Validate output against a pydantic schema. Raises ValidationError on failure."""
    schema.model_validate(output)


def assert_artifact_nonempty(artifact: dict) -> None:
    """Assert that an artifact dict has non-empty url, key, and size > 0."""
    assert artifact.get("url"), "artifact url is empty"
    assert artifact.get("key"), "artifact key is empty"
    assert artifact.get("size", 0) > 0, "artifact size is 0"
