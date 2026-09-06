from pathlib import Path

import pytest

from workers.e2e_targets import DeployedRunner, LocalTarget, deploy, undeploy
from workers.services.deps.dep_check import check_worker
from workers.services.mock_server.beam.fake import clear as beam_clear
from workers.services.mock_server.flash.fake import clear as flash_clear
from workers.services.mock_server.modal.fake import clear as modal_clear
from workers.services.platform.beam_platform_local import LocalBeamPlatform
from workers.services.platform.flash_platform_local import LocalFlashPlatform
from workers.services.platform.modal_platform_local import LocalModalPlatform
from workers.services.storage.r2_storage_fake import FakeR2Storage


def pytest_addoption(parser):
    parser.addoption("--target", action="store", default="fake", choices=("fake", "live"))


@pytest.fixture
def bucket():
    return FakeR2Storage()


def worker_path_for(test_path):
    test_file = Path(str(test_path))
    worker_file = test_file.parent.parent / test_file.name.replace("test_e2e_", "", 1)
    if not worker_file.exists():
        raise LookupError(f"no worker file for {test_file}")
    return str(worker_file)


@pytest.fixture(scope="session", autouse=True)
def local_fake_session():
    platforms = (LocalFlashPlatform(), LocalBeamPlatform(), LocalModalPlatform())
    for platform in platforms:
        platform.deploy()
    try:
        yield
    finally:
        for platform in platforms:
            platform.undeploy()


@pytest.fixture(scope="module", autouse=True)
def clear_fakes():
    flash_clear()
    beam_clear()
    modal_clear()
    yield
    flash_clear()
    beam_clear()
    modal_clear()


@pytest.fixture(scope="module")
def deployed_worker(request):
    path = worker_path_for(request.node.fspath)
    name, output = deploy(path)
    try:
        yield DeployedRunner(path, output)
    finally:
        undeploy(path, name)


@pytest.fixture
def e2e_target(monkeypatch, request):
    if request.node.get_closest_marker("deployed_e2e"):
        if request.config.getoption("target") != "live":
            pytest.skip("deployed-only; rerun with --target live")
        return request.getfixturevalue("deployed_worker")
    # pre-flight dep parity for local e2e
    worker_path = worker_path_for(request.node.fspath)
    check_worker(worker_path)
    return LocalTarget(monkeypatch)
