"""E2E local tests for krea2 flash worker.

Flash DI pattern: RemoteClassWrapper wraps the class.
Access raw class via wrapper.__dict__["_class_type"], inject pipe, call generate().
"""
import sys
import types
import pytest
from PIL import Image


class FakeTorch:
    class Generator:
        def __init__(self, device=None):
            pass
        def manual_seed(self, seed):
            return self


class FakePipeline:
    def __init__(self, model_id=None, **kwargs):
        self.model_id = model_id
        self.kwargs = kwargs
        self.torch = FakeTorch()

    def set_adapters(self, adapters, weights):
        pass

    def load_lora_weights(self, *args, **kwargs):
        pass

    def enable_model_cpu_offload(self):
        pass

    def __call__(self, prompt=None, height=768, width=768,
                 guidance_scale=0.0, num_inference_steps=8,
                 generator=None, image=None, **kwargs):
        fake_img = Image.new("RGB", (width, height), color="red")
        class FakeOutput:
            images = [fake_img]
        return FakeOutput()


class FakeS3:
    def put_object(self, **kwargs):
        pass

    def generate_presigned_url(self, operation, Params, ExpiresIn):
        bucket = Params["Bucket"]
        key = Params["Key"]
        return f"https://test.r2.cloudflarestorage.com/{bucket}/{key}?X-Amz-Signature=fake"


def _mock_runpod_flash():
    flash_mock = types.ModuleType("runpod_flash")

    class FakeGpuGroup:
        AMPERE_48 = "AMPERE_48"
        ADA_48_PRO = "ADA_48_PRO"

    def FakeEndpoint(**kw):
        def dec(cls):
            cls.__wrapped__ = cls
            return cls
        return dec

    flash_mock.Endpoint = FakeEndpoint
    flash_mock.GpuGroup = FakeGpuGroup
    return flash_mock


def _ensure_flash_mocked():
    if "runpod_flash" not in sys.modules:
        sys.modules["runpod_flash"] = _mock_runpod_flash()


def _make_raw_worker(monkeypatch, pipe=None):
    _ensure_flash_mocked()

    monkeypatch.setenv("R2_BUCKET", "generated-media")
    monkeypatch.setenv("R2_ENDPOINT", "https://test.r2.cloudflarestorage.com")
    monkeypatch.setenv("R2_ACCESS_KEY", "test-access")
    monkeypatch.setenv("R2_SECRET_KEY", "test-secret")
    monkeypatch.setenv("HF_TOKEN", "test-token")

    import boto3
    monkeypatch.setattr(boto3, "client", lambda *a, **kw: FakeS3())

    if "worker_flash_cls_krea2_ref2img" in sys.modules:
        del sys.modules["worker_flash_cls_krea2_ref2img"]

    from worker_flash_cls_krea2_ref2img import Krea2Ref2ImgWorker
    fake_pipe = pipe if pipe else FakePipeline()
    raw_cls = Krea2Ref2ImgWorker.__wrapped__

    import transformers.models.qwen3_vl.modeling_qwen3_vl as _q3vl_modeling
    orig_q3vl_rope_init = _q3vl_modeling.Qwen3VLTextRotaryEmbedding.__init__

    def _safe_rope_init(self_rope, config, device=None):
        if getattr(config, "rope_scaling", None) is None:
            config.rope_scaling = {
                "rope_type": "default",
                "mrope_section": [24, 20, 20],
            }
        orig_q3vl_rope_init(self_rope, config, device)

    _q3vl_modeling.Qwen3VLTextRotaryEmbedding.__init__ = _safe_rope_init

    import os
    import pathlib

    class FakeRuntimeDir(pathlib.Path):
        def glob(self, pattern):
            return []

    def fake_snapshot_download(*args, **kwargs):
        return FakeRuntimeDir("/fake/runtime/dir")

    import huggingface_hub
    monkeypatch.setattr(huggingface_hub, "snapshot_download", fake_snapshot_download)

    import transformers
    monkeypatch.setattr(transformers.AutoTokenizer, "from_pretrained", classmethod(lambda cls, *a, **kw: None))

    import diffusers
    monkeypatch.setattr(diffusers.DiffusionPipeline, "from_pretrained", classmethod(lambda cls, *a, **kw: fake_pipe))

    from typing import Optional, Literal
    raw_cls.Input.model_rebuild(_types_namespace={"_Optional": Optional, "_Literal": Literal})

    raw = raw_cls()
    raw.pipe = fake_pipe
    raw.torch = FakeTorch()
    return raw


def test_e2e_generate_invalid_input_rejects(monkeypatch):
    raw = _make_raw_worker(monkeypatch)
    with pytest.raises(Exception):
        raw.generate(prompt=None)


def test_e2e_generate_good_inference_fail_returns_contract(monkeypatch):
    raw = _make_raw_worker(monkeypatch)

    class FailingPipeline:
        def __init__(self):
            self.torch = FakeTorch()
        def set_adapters(self, adapters, weights):
            pass
        def load_lora_weights(self, *args, **kwargs):
            pass
        def enable_model_cpu_offload(self):
            pass
        def __call__(self, **kw):
            raise RuntimeError("inference failed")

    raw.pipe = FailingPipeline()
    with pytest.raises(RuntimeError, match="inference failed"):
        raw.generate(prompt="a cat")


def test_e2e_generate_good_inference_success_returns_contract(monkeypatch):
    raw = _make_raw_worker(monkeypatch)
    result = raw.generate(prompt="a cat", seed=42)

    assert "artifact" in result
    assert result["artifact"]["presigned_url"].startswith("https://test.r2.cloudflarestorage.com/generated-media/")


def test_e2e_generate_good_inference_success_uploads_artifact(monkeypatch):
    raw = _make_raw_worker(monkeypatch)
    result = raw.generate(prompt="a cat", seed=42)

    assert "artifact" in result
    assert result["artifact"]["presigned_url"].startswith("https://test.r2.cloudflarestorage.com/generated-media/")
