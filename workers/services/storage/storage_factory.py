from workers.services.storage.fake_r2 import FakeR2Storage
from workers.services.storage.real_r2 import RealR2Storage


def storage_factory(target):
    """Target-only storage factory. No `if target` anywhere else."""
    if target == "fake":
        return FakeR2Storage()
    if target == "live":
        return RealR2Storage()
    raise ValueError(f"unknown target: {target!r}")
