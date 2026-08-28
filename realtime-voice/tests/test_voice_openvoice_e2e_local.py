import pytest

from tests.e2e_local.conftest import check_deps


def test_deps_import():
    bad = check_deps("voice_openvoice")
    assert not bad, f"deps failed to import: {bad}"
