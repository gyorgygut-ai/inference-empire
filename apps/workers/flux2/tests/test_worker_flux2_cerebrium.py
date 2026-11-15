import io
import sys
from types import SimpleNamespace
from typing import cast

import pytest
from PIL import Image
from pydantic import ValidationError
from shared.fakes.image_pipe_fake import FakeImagePipe
from shared.fakes.torch_module_fake import FakeTorchModule

import apps.workers.flux2.worker_flux2_cerebrium as worker_mod
from apps.workers.flux2.shared.worker_flux2 import download_models


def _reset_runtime(monkeypatch):
    monkeypatch.setattr(worker_mod, "_storage", None)
    monkeypatch.setattr(worker_mod, "_pipe", None)
    monkeypatch.setattr(worker_mod, "_torch_module", None)


def test_generate_lazily_loads_persistent_model_and_returns_downloadable_png(
    monkeypatch, bucket
):
    image = Image.new("RGB", (8, 8), "red")
    pipeline = FakeImagePipe(image)
    torch_module = FakeTorchModule()
    cache_paths = []
    _reset_runtime(monkeypatch)
    monkeypatch.setattr(
        worker_mod,
        "load_dependencies",
        lambda: (bucket, None, torch_module),
    )
    monkeypatch.setattr(
        worker_mod,
        "load_pipeline_lazy",
        lambda cache_dir: cache_paths.append(cache_dir) or (pipeline, torch_module),
    )

    output = worker_mod.generate(prompt="a red square", seed=7)

    assert cache_paths == ["/persistent-storage/worker-flux2"]
    assert output["artifact"]["presigned_url"].startswith("https://")
    key = output["artifact"]["presigned_url"].rsplit("/", 1)[-1]
    downloaded = bucket.fetch(key)
    with Image.open(io.BytesIO(downloaded)) as artifact:
        artifact.verify()


def test_generate_rejects_invalid_contract_input(monkeypatch):
    _reset_runtime(monkeypatch)

    with pytest.raises(ValidationError):
        worker_mod.generate(prompt="a red square", height=cast("int", "invalid"))


def test_download_models_authenticates_and_uses_requested_cache(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setenv("SECRET_HUGGINGFACE_TOKEN", "hf-sentinel")
    monkeypatch.setitem(
        sys.modules,
        "huggingface_hub",
        SimpleNamespace(
            login=lambda **kwargs: calls.append(("login", kwargs)),
            snapshot_download=lambda **kwargs: calls.append(("download", kwargs))
            or str(tmp_path / "snapshot"),
        ),
    )

    download_models(cache_dir=tmp_path)

    assert calls[0] == (
        "login",
        {"token": "hf-sentinel", "add_to_git_credential": False},
    )
    assert calls[1][1]["token"] == "hf-sentinel"
    assert calls[1][1]["cache_dir"] == str(tmp_path / "flux2_klein9b_sdnq4")
