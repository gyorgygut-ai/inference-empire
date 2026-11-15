import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import apps.workers.flux2.prefetch_model as prefetch_model
import apps.workers.flux2.worker_flux2_azure as worker
from apps.workers.flux2.shared.fakes.image_pipe_fake import FakeImagePipe
from apps.workers.flux2.shared.fakes.torch_module_fake import FakeTorchModule


def test_health_does_not_load_model(monkeypatch):
    monkeypatch.setattr(worker, "load_pipeline_lazy", lambda **_: pytest.fail("model loaded"))
    response = TestClient(worker.app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_generate_uses_persistent_cache_and_returns_artifact(monkeypatch, bucket):
    image = Image.new("RGB", (8, 8), "red")
    pipe = FakeImagePipe(image)
    torch_module = FakeTorchModule()
    cache_paths = []
    monkeypatch.setattr(worker, "_storage", bucket)
    monkeypatch.setattr(worker, "_pipe", None)
    monkeypatch.setattr(worker, "_torch_module", torch_module)
    monkeypatch.setattr(
        worker,
        "load_pipeline_lazy",
        lambda cache_dir: cache_paths.append(cache_dir) or (pipe, torch_module),
    )

    response = TestClient(worker.app).post("/generate", json={"prompt": "red square"})

    assert response.status_code == 200
    artifact_url = response.json()["artifact"]["presigned_url"]
    assert cache_paths == [worker.MODEL_CACHE_DIR]
    key = artifact_url.rsplit("/", 1)[-1]
    with Image.open(io.BytesIO(bucket.fetch(key))) as artifact:
        artifact.verify()


def test_generate_rejects_invalid_contract():
    response = TestClient(worker.app).post("/generate", json={})
    assert response.status_code == 422


def test_prefetch_downloads_model_into_persistent_cache(monkeypatch, tmp_path):
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    (snapshot / "model.safetensors").write_bytes(b"weights")
    calls = []
    monkeypatch.setenv("FLUX2_MODEL_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(
        prefetch_model,
        "download_models",
        lambda cache_dir: calls.append(cache_dir) or {"flux2": snapshot},
    )

    prefetch_model.main()

    assert calls == [tmp_path / "cache"]
