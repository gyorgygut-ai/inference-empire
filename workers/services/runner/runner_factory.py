"""Target-only runner factories.

Fake = simulating classes (same interface, local execution). Real =
skeletons with NotImplementedError bodies until Todo 5 fills in the
provider CLI mechanics.
"""

from workers.services.runner.fake_runners import (
    FakeBeamAsyncRunner,
    FakeBeamSyncRunner,
    FakeFlashAsyncRunner,
    FakeFlashSyncRunner,
    FakeModalAsyncRunner,
    FakeModalSyncRunner,
)
from workers.services.runner.real_runners import (
    RealBeamAsyncRunner,
    RealBeamSyncRunner,
    RealFlashAsyncRunner,
    RealFlashSyncRunner,
    RealModalAsyncRunner,
    RealModalSyncRunner,
)


def flash_sync_runner_factory(target):
    if target == "fake":
        return FakeFlashSyncRunner()
    if target == "live":
        return RealFlashSyncRunner()
    raise ValueError(f"unknown target: {target!r}")


def flash_async_runner_factory(target):
    if target == "fake":
        return FakeFlashAsyncRunner()
    if target == "live":
        return RealFlashAsyncRunner()
    raise ValueError(f"unknown target: {target!r}")


def beam_sync_runner_factory(target):
    if target == "fake":
        return FakeBeamSyncRunner()
    if target == "live":
        return RealBeamSyncRunner()
    raise ValueError(f"unknown target: {target!r}")


def beam_async_runner_factory(target):
    if target == "fake":
        return FakeBeamAsyncRunner()
    if target == "live":
        return RealBeamAsyncRunner()
    raise ValueError(f"unknown target: {target!r}")


def modal_sync_runner_factory(target):
    if target == "fake":
        return FakeModalSyncRunner()
    if target == "live":
        return RealModalSyncRunner()
    raise ValueError(f"unknown target: {target!r}")


def modal_async_runner_factory(target):
    if target == "fake":
        return FakeModalAsyncRunner()
    if target == "live":
        return RealModalAsyncRunner()
    raise ValueError(f"unknown target: {target!r}")
