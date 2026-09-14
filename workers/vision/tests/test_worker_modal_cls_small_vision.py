import base64
import io

import pytest
from PIL import Image
from pydantic import ValidationError

import workers.vision.worker_modal_cls_small_vision as worker_mod
from workers.services.inference.vision_fake import FakeVisionModel, FakeVisionProcessor
from workers.vision._shared_small_vision import (
    SmallVisionInput,
    SmallVisionOutput,
    build_analyze_prompt,
    do_inference,
    resolve_analyze_prompt,
)


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


def test_do_inference_returns_output_contract():
    model = FakeVisionModel(CANNED)
    processor = FakeVisionProcessor(CANNED)
    prompt = build_analyze_prompt()
    req = SmallVisionInput(image_base64=_image_b64())
    out = do_inference(model, processor, prompt, req)
    assert out.description == "An 8x8 green square."


def test_generate_returns_classification():
    out = worker_mod.generate(FakeVisionModel(CANNED), FakeVisionProcessor(CANNED), "fake-prompt", image_base64=_image_b64())
    assert out == CANNED


def test_generate_rejects_missing_image():
    with pytest.raises(ValidationError):
        worker_mod.generate(FakeVisionModel(CANNED), FakeVisionProcessor(CANNED), "fake-prompt")


def test_generate_uses_default_when_prompt_omitted():
    req = SmallVisionInput(image_base64=_image_b64())
    assert req.prompt is None
    out = worker_mod.generate(FakeVisionModel(CANNED), FakeVisionProcessor(CANNED), "fake-prompt", image_base64=_image_b64())
    assert out == CANNED


def test_generate_uses_custom_prompt_override():
    seen: dict = {}

    class _RecordingProcessor(FakeVisionProcessor):
        def apply_chat_template(self, messages, **kwargs):
            seen["messages"] = messages
            return super().apply_chat_template(messages, **kwargs)

    out = worker_mod.generate(
        FakeVisionModel(CANNED),
        _RecordingProcessor(CANNED),
        "fake-default",
        image_base64=_image_b64(),
        prompt="custom detailed analyze instruction",
    )
    assert out == CANNED
    texts = [c.get("text", "") for m in seen["messages"] for c in m.get("content", []) if c.get("type") == "text"]
    assert any("custom detailed analyze instruction" in t for t in texts)


def test_resolve_analyze_prompt_prefers_override():
    assert resolve_analyze_prompt("default", None) == "default"
    assert resolve_analyze_prompt("default", "custom") == "custom"


def test_input_rejects_non_string_prompt():
    with pytest.raises(ValidationError):
        SmallVisionInput(image_base64=_image_b64(), prompt=123)


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
    model, _processor, _prompt = worker_mod.load_dependencies()
    assert model is fake_model
