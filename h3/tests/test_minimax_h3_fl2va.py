import importlib

import pytest

_has_torch = importlib.util.find_spec("torch") is not None


def test_deps_import():
    from tests.e2e_local.conftest import check_deps

    bad = check_deps("minimax_h3_fl2va")
    if bad:
        pytest.skip(f"deps not available locally: {bad}")
    assert not bad


def test_pip_check():
    from tests.e2e_local.conftest import check_pip

    code, out = check_pip()
    assert code == 0, f"pip check failed:\n{out}"


def test_module_import():
    from tests.e2e_local.conftest import WORKERS

    importlib.import_module(WORKERS["minimax_h3_fl2va"]["module"])


@pytest.mark.skipif(not _has_torch, reason="requires torch (remote Flash environment)")
def test_handler_output_valid():
    from tests.e2e_local.conftest import _tiny_png_b64, build_worker, validate_output

    worker = build_worker("minimax_h3_fl2va")
    import asyncio

    result = asyncio.get_event_loop().run_until_complete(
        worker.generate(prompt="a scene", first_frame=_tiny_png_b64())
    )
    dumped = validate_output(worker, result)
    assert set(dumped) == {"artifact"}


@pytest.mark.skipif(not _has_torch, reason="requires torch (remote Flash environment)")
def test_handler_artifact_nonempty():
    from tests.e2e_local.conftest import _tiny_png_b64, assert_artifact_nonempty, build_worker, validate_output

    worker = build_worker("minimax_h3_fl2va")
    import asyncio

    result = asyncio.get_event_loop().run_until_complete(
        worker.generate(prompt="a scene", first_frame=_tiny_png_b64())
    )
    dumped = validate_output(worker, result)
    assert_artifact_nonempty(dumped)


@pytest.mark.skipif(not _has_torch, reason="requires torch (remote Flash environment)")
def test_handler_negative_none_prompt():
    from pydantic import ValidationError
    from tests.e2e_local.conftest import build_worker

    worker = build_worker("minimax_h3_fl2va")
    import asyncio

    with pytest.raises(ValidationError):
        asyncio.get_event_loop().run_until_complete(
            worker.generate(prompt=None)
        )
