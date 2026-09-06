import base64
import io

import pytest
from PIL import Image
from pydantic import ValidationError

import workers.vision.worker_flash_cls_small_vision as worker_mod
from workers.vision._shared_small_vision import SmallVisionInput, SmallVisionOutput, build_analyze_prompt, do_inference
from workers.services.inference.vision_fake import FakeVisionModel, FakeVisionProcessor


def _image_b64():
    img = Image.new("RGB", (8, 8), (0, 255, 0))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


CANNED = {
    "classification": "landscape_0p",
    "subjects": ["green hill"],
    "description": "An 8x8 green square.",
}


def test_do_inference_requested_with_right_args():
    model = FakeVisionModel(CANNED)
    processor = FakeVisionProcessor(CANNED)
    prompt = build_analyze_prompt()
    req = SmallVisionInput(image_base64=_image_b64())
    out = do_inference(model, processor, prompt, req)
    assert isinstance(out, SmallVisionOutput)
    assert out.classification == "landscape_0p"


def test_do_inference_returns_output_contract():
    model = FakeVisionModel(CANNED)
    processor = FakeVisionProcessor(CANNED)
    prompt = build_analyze_prompt()
    req = SmallVisionInput(image_base64=_image_b64())
    out = do_inference(model, processor, prompt, req)
    assert isinstance(out, SmallVisionOutput)
    assert out.subjects == ["green hill"]
    assert out.description == "An 8x8 green square."


def test_generate_returns_classification():
    out = worker_mod.generate(FakeVisionModel(CANNED), FakeVisionProcessor(CANNED), "fake-prompt", image_base64=_image_b64())
    assert out == CANNED


def test_generate_rejects_missing_image():
    with pytest.raises(ValidationError):
        worker_mod.generate(FakeVisionModel(CANNED), FakeVisionProcessor(CANNED), "fake-prompt")


def test_do_inference_rejects_non_json():
    class _GarbageProcessor(FakeVisionProcessor):
        def decode(self, generated, **kwargs):
            return "not json at all"

    model = FakeVisionModel(CANNED)
    processor = _GarbageProcessor(CANNED)
    req = SmallVisionInput(image_base64=_image_b64())
    with pytest.raises(RuntimeError, match="non-JSON"):
        do_inference(model, processor, "fake-prompt", req)


def test_load_dependencies_mocked(monkeypatch):
    fake_model = FakeVisionModel(CANNED)
    fake_processor = FakeVisionProcessor(CANNED)
    fake_prompt = "fake-prompt"

    def fake_load(cache_dir=None):
        return fake_model, fake_processor, fake_prompt

    monkeypatch.setattr(worker_mod, "load_dependencies", fake_load)
    model, processor, prompt = worker_mod.load_dependencies()
    assert model is fake_model
    assert processor is fake_processor
    assert prompt == fake_prompt
