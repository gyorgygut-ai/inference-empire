import asyncio
import pytest
from pydantic import ValidationError

from tests.conftest import _load_worker

_cls = _load_worker("worker_minimax_h3_ref2va_comfy", "MiniMaxH3Ref2VAComfyWorker")
Input = _cls.Input
Output = _cls.Output


def test_input_valid():
    Input(prompt="a cinematic shot with <Picture 1>", ref_images=["abc"])


def test_input_prompt_required():
    with pytest.raises(ValidationError):
        Input(prompt=None)


def test_ref_images_limit():
    with pytest.raises(ValidationError):
        Input(prompt="test", ref_images=["img"] * 10)


def test_total_files_limit():
    with pytest.raises(ValidationError):
        Input(
            prompt="test",
            ref_images=["img"] * 5,
            ref_videos=["vid"] * 5,
            ref_audios=["aud"] * 3,
        )


def test_audio_without_visual_raises():
    with pytest.raises(ValidationError):
        Input(prompt="test", ref_audios=["aud"])


def test_output_valid():
    Output(
        artifact={"url": "https://r2.example.com/file.mp4", "key": "file.mp4", "size": 100},
        video="dGVzdA==",
    )


def test_generate_sunny():
    from tests.conftest import _tiny_png_b64

    inst = _cls()
    res = inst.generate(prompt="a scene with <Picture 1>", ref_images=[_tiny_png_b64()])
    dumped = Output.model_validate(res).model_dump()
    assert set(dumped) == {"artifact", "video"}
    assert dumped["artifact"]["url"].startswith("https://")
    assert dumped["artifact"]["size"] > 0
    assert dumped["video"] == "dGVzdA=="

