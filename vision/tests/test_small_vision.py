import importlib

import pytest
from pydantic import ValidationError

from tests.e2e_local.conftest import (
    WORKERS,
    _tiny_png_b64,
    check_deps,
)

WORKER = "small_vision"
CFG = WORKERS[WORKER]

_has_torch = importlib.util.find_spec("torch") is not None


def test_deps_import():
    from tests.e2e_local.conftest import check_deps

    bad = check_deps(WORKER)
    if bad:
        pytest.skip(f"deps not available locally: {bad}")
    assert not bad


def test_pip_check():
    from tests.e2e_local.conftest import check_pip

    code, out = check_pip()
    assert code == 0, f"pip check failed:\n{out}"


def test_module_import():
    importlib.import_module(CFG["module"])


@pytest.mark.skipif(not _has_torch, reason="requires torch (remote Flash environment)")
def test_handler_output_valid():
    from tests.e2e_local.conftest import build_worker, validate_output

    worker = build_worker(WORKER)
    import asyncio

    result = asyncio.get_event_loop().run_until_complete(
        worker.analyze(image_base64=_tiny_png_b64())
    )
    dumped = validate_output(worker, result)
    assert set(dumped) == {"classification", "subjects", "description"}


@pytest.mark.skipif(not _has_torch, reason="requires torch (remote Flash environment)")
def test_handler_classification_in_enum():
    from tests.e2e_local.conftest import build_worker, validate_output

    worker = build_worker(WORKER)
    import asyncio

    result = asyncio.get_event_loop().run_until_complete(
        worker.analyze(image_base64=_tiny_png_b64())
    )
    dumped = validate_output(worker, result)
    allowed = worker.Output.model_fields["classification"].annotation
    assert dumped["classification"] in allowed.__args__


@pytest.mark.skipif(not _has_torch, reason="requires torch (remote Flash environment)")
def test_handler_subjects_nonempty_strings():
    from tests.e2e_local.conftest import build_worker, validate_output

    worker = build_worker(WORKER)
    import asyncio

    result = asyncio.get_event_loop().run_until_complete(
        worker.analyze(image_base64=_tiny_png_b64())
    )
    dumped = validate_output(worker, result)
    assert isinstance(dumped["subjects"], list)
    assert dumped["subjects"]
    assert all(isinstance(s, str) for s in dumped["subjects"])


@pytest.mark.skipif(not _has_torch, reason="requires torch (remote Flash environment)")
def test_handler_description_nonempty():
    from tests.e2e_local.conftest import build_worker, validate_output

    worker = build_worker(WORKER)
    import asyncio

    result = asyncio.get_event_loop().run_until_complete(
        worker.analyze(image_base64=_tiny_png_b64())
    )
    dumped = validate_output(worker, result)
    assert isinstance(dumped["description"], str) and dumped["description"]


@pytest.mark.skipif(not _has_torch, reason="requires torch (remote Flash environment)")
def test_handler_negative_none_image():
    from tests.e2e_local.conftest import build_worker

    worker = build_worker(WORKER)
    import asyncio

    with pytest.raises(ValidationError):
        asyncio.get_event_loop().run_until_complete(
            worker.analyze(image_base64=None)
        )
