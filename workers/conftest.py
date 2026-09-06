import os

import pytest

from workers.e2e_targets import DeployedTarget, LocalTarget
from workers.services.storage.r2_storage_fake import FakeR2Storage


@pytest.fixture
def bucket():
    return FakeR2Storage()


@pytest.fixture
def e2e_target(monkeypatch, request):
    if request.node.get_closest_marker("deployed_e2e"):
        return DeployedTarget(os.environ["TEST_ENV_URL"])
    return LocalTarget(monkeypatch)
