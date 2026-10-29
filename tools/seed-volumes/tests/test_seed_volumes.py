from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "seed-volumes.py"
SPEC = importlib.util.spec_from_file_location("seed_volumes", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
seed_volumes = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = seed_volumes
SPEC.loader.exec_module(seed_volumes)


def test_discovers_worker_models_without_importing_worker_modules() -> None:
    models = seed_volumes.declared_models()
    by_name = {model.name: model for model in models}

    assert set(by_name) == {
        "flux2_klein9b_sdnq4",
        "segmind_tiny_sd",
        "qwen2_vl_2b_instruct",
        "qwen2_5_3b_instruct",
        "faster_whisper_large_v3",
        "resembleai_chatterbox_tts",
    }
    assert by_name["flux2_klein9b_sdnq4"].repo_id == (
        "Disty0/FLUX.2-klein-9B-SDNQ-4bit-dynamic-svd-r32"
    )
    assert by_name["faster_whisper_large_v3"].volume == (
        "model-cache-faster_whisper_large_v3"
    )


def test_existing_volumes_reads_beam_json(monkeypatch) -> None:
    monkeypatch.setattr(
        seed_volumes,
        "run_beam",
        lambda *_args: '[{"name":"model-cache-one"},{"name":"hf-cache"}]',
    )

    assert seed_volumes.existing_volumes() == {"model-cache-one", "hf-cache"}


def test_json_payload_strips_beam_terminal_colors() -> None:
    assert seed_volumes._json_payload('\x1b[1m[\x1b[0m{"name":"cache"}\x1b[1m]\x1b[0m') == [
        {"name": "cache"}
    ]


def test_snapshot_completeness_requires_every_expected_file(monkeypatch) -> None:
    listings = iter(
        [
            '[{"name":"config.json","is_dir":false},'
            '{"name":"unet","is_dir":true}]',
            '[{"name":"diffusion_pytorch_model.safetensors","is_dir":false}]',
        ]
    )
    monkeypatch.setattr(seed_volumes, "run_beam", lambda *_args: next(listings))

    assert seed_volumes.snapshot_is_complete(
        "volume",
        "models--org--model/snapshots/revision",
        ["config.json", "unet/diffusion_pytorch_model.safetensors"],
    )

    monkeypatch.setattr(
        seed_volumes,
        "_walk_volume",
        lambda *_args: {"config.json"},
    )
    assert not seed_volumes.snapshot_is_complete(
        "volume",
        "snapshot",
        ["config.json", "missing.safetensors"],
    )


def test_temporary_download_is_removed_after_copy_failure(monkeypatch, tmp_path: Path) -> None:
    model = seed_volumes.Model(
        name="tiny",
        repo_id="org/model",
        cache_path="./model-cache/tiny",
        volume="model-cache-tiny",
        declaration=tmp_path / "worker.py",
    )
    temporary_roots: list[Path] = []

    class Api:
        def __init__(self, token=None):
            pass

        def model_info(self, _repo_id):
            return type("Info", (), {"sha": "revision"})()

        def list_repo_files(self, _repo_id, revision):
            assert revision == "revision"
            return ["config.json"]

    def download(*, repo_id, revision, cache_dir, token):
        assert (repo_id, revision) == ("org/model", "revision")
        repo_dir = cache_dir / "models--org--model"
        repo_dir.mkdir(parents=True)
        temporary_roots.append(cache_dir.parent)
        return str(repo_dir / "snapshots" / revision)

    monkeypatch.setitem(
        sys.modules,
        "huggingface_hub",
        type("Hub", (), {"HfApi": Api, "snapshot_download": download}),
    )
    monkeypatch.setattr(
        seed_volumes,
        "run_beam",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("copy failed")),
    )
    monkeypatch.setattr(seed_volumes, "snapshot_is_complete", lambda *_args: False)

    try:
        seed_volumes.seed_model(model, {"model-cache-tiny"})
    except RuntimeError as error:
        assert "copy failed" in str(error)
    else:
        raise AssertionError("expected Beam copy failure")

    assert temporary_roots
    assert not temporary_roots[0].exists()


def test_temporary_download_is_removed_after_verification_failure(
    monkeypatch, tmp_path: Path
) -> None:
    model = seed_volumes.Model(
        name="tiny",
        repo_id="org/model",
        cache_path="./model-cache/tiny",
        volume="model-cache-tiny",
        declaration=tmp_path / "worker.py",
    )
    temporary_roots: list[Path] = []

    class Api:
        def __init__(self, token=None):
            pass

        def model_info(self, _repo_id):
            return type("Info", (), {"sha": "revision"})()

        def list_repo_files(self, _repo_id, revision):
            return ["config.json"]

    def download(*, repo_id, revision, cache_dir, token):
        repo_dir = cache_dir / "models--org--model"
        repo_dir.mkdir(parents=True)
        temporary_roots.append(cache_dir.parent)
        return str(repo_dir / "snapshots" / revision)

    monkeypatch.setitem(
        sys.modules,
        "huggingface_hub",
        type("Hub", (), {"HfApi": Api, "snapshot_download": download}),
    )
    monkeypatch.setattr(seed_volumes, "run_beam", lambda *_args: "")
    monkeypatch.setattr(seed_volumes, "snapshot_is_complete", lambda *_args: False)

    try:
        seed_volumes.seed_model(model, {"model-cache-tiny"})
    except RuntimeError as error:
        assert "complete snapshot after upload" in str(error)
    else:
        raise AssertionError("expected remote verification failure")

    assert temporary_roots
    assert not temporary_roots[0].exists()


def test_temporary_download_is_removed_after_download_failure(monkeypatch, tmp_path: Path) -> None:
    model = seed_volumes.Model(
        name="tiny",
        repo_id="org/model",
        cache_path="./model-cache/tiny",
        volume="model-cache-tiny",
        declaration=tmp_path / "worker.py",
    )
    temporary_roots: list[Path] = []

    class Api:
        def __init__(self, token=None):
            pass

        def model_info(self, _repo_id):
            return type("Info", (), {"sha": "revision"})()

        def list_repo_files(self, _repo_id, revision):
            return ["config.json"]

    def download(*, cache_dir, **_kwargs):
        temporary_roots.append(cache_dir.parent)
        raise RuntimeError("download failed")

    monkeypatch.setitem(
        sys.modules,
        "huggingface_hub",
        type("Hub", (), {"HfApi": Api, "snapshot_download": download}),
    )
    monkeypatch.setattr(seed_volumes, "run_beam", lambda *_args: "[]")

    try:
        seed_volumes.seed_model(model, {"model-cache-tiny"})
    except RuntimeError as error:
        assert "download failed" in str(error)
    else:
        raise AssertionError("expected Hugging Face download failure")

    assert temporary_roots
    assert not temporary_roots[0].exists()
