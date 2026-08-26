import importlib

import pytest
from pydantic import ValidationError

from tests.e2e_local.conftest import (
    WORKERS,
    _tiny_png_b64,
    build_worker,
    check_deps,
    check_pip,
    validate_output,
)

WORKER = "small_vision"
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
    result = worker.analyze(image_base64=_tiny_png_b64())
    dumped = validate_output(worker, result)
    assert set(dumped) == {"classification", "subjects", "description"}


def test_handler_classification_in_enum(worker):
    result = worker.analyze(image_base64=_tiny_png_b64())
    dumped = validate_output(worker, result)
    allowed = worker.Output.model_fields["classification"].annotation
    assert dumped["classification"] in allowed.__args__


def test_handler_subjects_nonempty_strings(worker):
    result = worker.analyze(image_base64=_tiny_png_b64())
    dumped = validate_output(worker, result)
    assert isinstance(dumped["subjects"], list)
    assert dumped["subjects"]
    assert all(isinstance(s, str) for s in dumped["subjects"])


def test_handler_description_nonempty(worker):
    result = worker.analyze(image_base64=_tiny_png_b64())
    dumped = validate_output(worker, result)
    assert isinstance(dumped["description"], str) and dumped["description"]


def test_handler_negative_none_image(worker):
    with pytest.raises(ValidationError):
        worker.analyze(image_base64=None)
