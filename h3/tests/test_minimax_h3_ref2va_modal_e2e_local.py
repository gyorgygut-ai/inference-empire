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

WORKER = "minimax_h3_ref2va_modal"
CFG = WORKERS.get(WORKER, {})


@pytest.fixture(scope="module")
def worker():
    return build_worker(WORKER)


def test_deps_import():
    bad = check_deps(WORKER)
    assert not bad, f"deps failed to import: {bad}"


def test_pip_check():
    bad = check_pip(WORKER)
    assert not bad, f"pip packages failed: {bad}"


def test_module_import():
    mod = importlib.import_module(CFG.get("module", "worker_modal_cls_minimax_h3_ref2va"))
    assert hasattr(mod, "MiniMaxH3Ref2VAInput")
    assert hasattr(mod, "MiniMaxH3Ref2VAOutput")


def test_handler_negative_none_prompt(worker):
    with pytest.raises(ValidationError):
        from worker_modal_cls_minimax_h3_ref2va import MiniMaxH3Ref2VAInput

        MiniMaxH3Ref2VAInput(prompt=None)
