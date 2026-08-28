import importlib

import pytest


def test_module_import():
    mod = importlib.import_module("worker_beam_asgi_realtime_voice_openvoice")
    assert hasattr(mod, "worker")
    assert hasattr(mod, "image")
