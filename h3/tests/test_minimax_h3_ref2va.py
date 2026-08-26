import importlib

import pytest
from pydantic import ValidationError

from tests.e2e_local.conftest import (
    WORKERS,
    _tiny_png_b64,
    assert_artifact_nonempty,
    build_worker,
    check_deps,
    check_pip,
    validate_output,
)

WORKER = "minimax_h3_ref2va"
CFG = WORKERS[WORKER]


@pytest.fixture(scope="module")
def worker():
    return build_worker(WORKER)


# --- dependency checks ---


def test_deps_import():
    bad = check_deps(WORKER)
    assert not bad, f"deps failed to import: {bad}"


def test_pip_check():
    code, out = check_pip()
    assert code == 0, f"pip check failed:\n{out}"


def test_module_import():
    importlib.import_module(CFG["module"])


# --- handler execution ---


def test_handler_output_valid(worker):
    result = worker.generate(prompt="a scene", ref_images=[_tiny_png_b64()])
    dumped = validate_output(worker, result)
    assert set(dumped) == {"artifact"}


def test_handler_artifact_nonempty(worker):
    result = worker.generate(prompt="a scene", ref_images=[_tiny_png_b64()])
    dumped = validate_output(worker, result)
    assert_artifact_nonempty(dumped)


def test_handler_negative_none_prompt(worker):
    with pytest.raises(ValidationError):
        worker.generate(prompt=None)


def test_handler_negative_too_many_ref_images(worker):
    with pytest.raises(ValidationError):
        worker.generate(prompt="a", ref_images=["<base64>"] * 10)


def test_handler_negative_audio_without_visual(worker):
    with pytest.raises(ValidationError):
        worker.generate(prompt="a", ref_audios=[_tiny_png_b64()])
