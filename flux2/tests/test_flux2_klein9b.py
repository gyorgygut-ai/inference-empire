import importlib

import pytest
from pydantic import ValidationError

from tests.e2e_local.conftest import (
    WORKERS,
    assert_artifact_nonempty,
    build_worker,
    check_deps,
    check_pip,
    validate_output,
)

WORKER = "flux2_klein9b"
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
    result = worker.generate(prompt="a cat")
    dumped = validate_output(worker, result)
    assert set(dumped) == {"artifact"}


def test_handler_artifact_nonempty(worker):
    result = worker.generate(prompt="a cat")
    dumped = validate_output(worker, result)
    assert_artifact_nonempty(dumped)


def test_handler_negative_none_prompt(worker):
    with pytest.raises(ValidationError):
        worker.generate(prompt=None)
