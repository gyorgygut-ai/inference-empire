import pytest


def test_handler_negative_none_prompt():
    from pydantic import ValidationError

    from worker_modal_cls_minimax_h3_ref2va import MiniMaxH3Ref2VAInput

    with pytest.raises(ValidationError):
        MiniMaxH3Ref2VAInput(prompt=None)
