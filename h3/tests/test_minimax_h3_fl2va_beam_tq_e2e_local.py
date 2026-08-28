import importlib

import pytest


def test_module_import():
    mod = importlib.import_module("worker_beam_tq_minimax_h3_fl2va")
    assert hasattr(mod, "MiniMaxH3Fl2VAInput")
    assert hasattr(mod, "MiniMaxH3Fl2VAOutput")
    assert hasattr(mod, "load_pipeline")


def test_handler_negative_none_prompt():
    from pydantic import ValidationError

    from worker_beam_tq_minimax_h3_fl2va import MiniMaxH3Fl2VAInput

    with pytest.raises(ValidationError):
        MiniMaxH3Fl2VAInput(prompt=None)
