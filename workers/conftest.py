import pytest

from workers.services.storage.r2_storage_fake import FakeR2Storage


@pytest.fixture
def bucket():
    return FakeR2Storage()
