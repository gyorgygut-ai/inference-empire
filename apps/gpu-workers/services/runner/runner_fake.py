"""Fake runners: per-provider names over the shared runner vocabulary.

Behavior is identical across providers today — the subclasses exist so each
worker's platform addresses a named runner. Untouched behavior.
"""

from apps.gpu_workers.services.runner.runner import AsyncRunner, SyncRunner


class FakeSyncRunner(SyncRunner):
    """Named home for future sync quirks — none today."""


class FakeAsyncRunner(AsyncRunner):
    """Named home for future async quirks — none today."""


class FakeFlashSyncRunner(FakeSyncRunner):
    """Named home for future Flash sync quirks — none today."""


class FakeFlashAsyncRunner(FakeAsyncRunner):
    """Named home for future Flash async quirks — none today."""


class FakeBeamSyncRunner(FakeSyncRunner):
    """Named home for future Beam sync quirks — none today."""


class FakeBeamAsyncRunner(FakeAsyncRunner):
    """Named home for future Beam async quirks — none today."""


class FakeModalSyncRunner(FakeSyncRunner):
    """Named home for future Modal sync quirks — none today."""


class FakeModalAsyncRunner(FakeAsyncRunner):
    """Named home for future Modal async quirks — none today."""
