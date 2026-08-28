import pytest


def test_handler_negative_none_prompt():
    from pydantic import ValidationError

    from worker_beam_tq_minimax_h3_ref2va_comfy import Input

    with pytest.raises(ValidationError):
        Input(prompt=None)
