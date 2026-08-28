import importlib

import pytest


def test_module_import():
    mod = importlib.import_module("worker_beam_asgi_realtime_voice_qwen")
    assert hasattr(mod, "worker")
    assert hasattr(mod, "image")
    assert hasattr(mod, "load_models")


def test_ensure_model_skips_existing(tmp_path):
    from worker_beam_asgi_realtime_voice_qwen import ensure_model

    d = tmp_path / "model"
    d.mkdir()
    (d / "dummy.txt").write_text("x")
    ensure_model(str(d), "nonexistent/repo")
    assert (d / "dummy.txt").exists()
