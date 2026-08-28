import pytest


def test_handler_negative_none_prompt():
    from pydantic import ValidationError

    from worker_modal_cls_minimax_h3_fl2va import MiniMaxH3Fl2VAInput

    with pytest.raises(ValidationError):
        MiniMaxH3Fl2VAInput(prompt=None)
