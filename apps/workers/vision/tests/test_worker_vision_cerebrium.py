import base64
import io
from typing import cast

import pytest
from PIL import Image
from pydantic import ValidationError
from shared.fakes.vision_fake import FakeVisionModel, FakeVisionProcessor

import apps.workers.vision.worker_vision_cerebrium as worker_mod


def _image_b64() -> str:
    image = Image.new("RGB", (8, 8), (0, 255, 0))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _reset(monkeypatch):
    monkeypatch.setattr(worker_mod, "_model", None)
    monkeypatch.setattr(worker_mod, "_processor", None)
    monkeypatch.setattr(worker_mod, "_analyze_prompt", None)


def test_generate_lazily_loads_model_and_returns_output(monkeypatch):
    canned = {
        "classification": "landscape_0p",
        "subjects": ["green square"],
        "description": "An 8x8 green square.",
    }
    model = FakeVisionModel(canned)
    processor = FakeVisionProcessor(canned)
    cache_paths = []
    _reset(monkeypatch)
    monkeypatch.setattr(
        worker_mod,
        "load_pipeline_lazy",
        lambda cache_dir: cache_paths.append(cache_dir)
        or (model, processor, "default analyze prompt"),
    )

    result = worker_mod.generate(image_base64=_image_b64())

    assert result == canned
    assert cache_paths == ["/persistent-storage/worker-vision"]


def test_generate_rejects_missing_image_without_loading(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setattr(
        worker_mod,
        "load_pipeline_lazy",
        lambda **_kwargs: pytest.fail("invalid input must not load the model"),
    )

    with pytest.raises(ValidationError):
        worker_mod.generate(image_base64=cast("str", None))
