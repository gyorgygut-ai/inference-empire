import importlib
import io
import sys
from types import ModuleType

import pytest
from PIL import Image
from pydantic import ValidationError
from shared.fakes.image_pipe_fake import FakeImagePipe
from shared.fakes.torch_module_fake import FakeTorchModule

from apps.workers.flux2.shared.worker_flux2 import Flux2Klein9bInput

fal_stub = ModuleType("fal")
fal_stub.App = type("App", (), {})
fal_stub.endpoint = lambda _: lambda function: function
sys.modules["fal"] = fal_stub
worker_mod = importlib.import_module("apps.workers.flux2.worker_flux2_fal")


def _png_bytes(image):
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _worker():
    return worker_mod.FluxKleinWorker.__new__(worker_mod.FluxKleinWorker)


def test_fal_generate_lazily_loads_pipeline_and_returns_r2_artifact(monkeypatch, bucket):
    image = Image.new("RGB", (8, 8), (255, 0, 0))
    pipe = FakeImagePipe(image)
    torch_module = FakeTorchModule()
    worker = _worker()
    worker.storage = bucket
    worker.pipe = None
    worker.torch_module = None
    calls = []

    def load_pipeline():
        calls.append(True)
        return pipe, torch_module

    monkeypatch.setattr(worker_mod, "load_pipeline_lazy", load_pipeline)
    result = worker.generate(Flux2Klein9bInput(prompt="a red square", seed=7))

    key = result["artifact"]["presigned_url"].rsplit("/", 1)[-1].split("?", 1)[0]
    assert calls == [True]
    assert bucket.fetch(key) == _png_bytes(image)


def test_fal_generate_rejects_missing_prompt():
    with pytest.raises(ValidationError):
        Flux2Klein9bInput.model_validate({})


def test_fal_app_limits_instances_and_exposes_only_worker_secrets():
    assert worker_mod.FluxKleinWorker.min_concurrency == 0
    assert worker_mod.FluxKleinWorker.max_concurrency == 1
    assert worker_mod.FluxKleinWorker.secrets == [
        "SECRET_HUGGINGFACE_TOKEN",
        "SECRET_R2_ACCESS_KEY",
        "SECRET_R2_SECRET_KEY",
        "SECRET_R2_ENDPOINT",
        "SECRET_R2_BUCKET",
    ]
