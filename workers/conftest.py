from pathlib import Path

import pytest

from workers.e2e_targets import DeployedRunner, LocalTarget, deploy, undeploy
from workers.services.storage.r2_storage_fake import FakeR2Storage


@pytest.fixture
def bucket():
    return FakeR2Storage()


def worker_path_for(test_path):
    test_file = Path(str(test_path))
    worker_file = test_file.parent.parent / test_file.name.replace("test_e2e_", "", 1)
    if not worker_file.exists():
        raise LookupError(f"no worker file for {test_file}")
    return str(worker_file)


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
        return request.getfixturevalue("deployed_worker")
    return LocalTarget(monkeypatch)
