import asyncio
import pytest
from pydantic import ValidationError

from tests.conftest import _load_worker

_cls = _load_worker("worker_flash_cls_minimax_h3_comfy", "MiniMaxH3ComfyWorker")
Input = _cls.Input
Output = _cls.Output


def test_input_valid():
    Input(prompt="a cinematic shot of a cat")


def test_input_prompt_required():
    with pytest.raises(ValidationError):
        Input(prompt=None)


def test_output_valid():
    Output(
        artifact={"url": "https://r2.example.com/file.mp4", "key": "file.mp4", "size": 100},
        video="dGVzdA==",
    )


def test_generate_sunny():
    from tests.conftest import _tiny_png_b64

    inst = _cls()
    res = inst.generate(prompt="a cat walking", first_frame=_tiny_png_b64())
    dumped = Output.model_validate(res).model_dump()
    assert set(dumped) == {"artifact", "video"}
    assert dumped["artifact"]["url"].startswith("https://")
    assert dumped["artifact"]["size"] > 0
    assert dumped["video"] == "dGVzdA=="

