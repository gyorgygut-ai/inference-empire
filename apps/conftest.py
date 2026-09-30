import sys
import types

import pytest

from packages.storage.r2_storage_fake import FakeR2Storage


@pytest.fixture
def bucket():
    return FakeR2Storage()


class _FluentMeta(type):
    def __getattr__(cls, name):
        return lambda *args, **kwargs: _Fluent()


class _Fluent(metaclass=_FluentMeta):
    """Import-time stand-in for beam SDK builders (Image/Volume/Autoscaler)."""

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        return lambda *args, **kwargs: self


class _TaskQueueStub:
    """Mimics the beam TaskQueue local-run surface used by unit tests."""

    def __init__(self, fn):
        self._fn = fn

    def __call__(self, *args, **kwargs):
        return self._fn(*args, **kwargs)

    def local(self, context, **kwargs):
        return self._fn(context, **kwargs)


def _task_queue_stub(**kwargs):
    def deco(fn):
        return _TaskQueueStub(fn)

    return deco


def _install_beam_stub():
    mod = types.ModuleType("beam")
    mod.Image = _Fluent
    mod.QueueDepthAutoscaler = _Fluent
    mod.Volume = _Fluent
    mod.task_queue = _task_queue_stub
    sys.modules["beam"] = mod


def pytest_configure(config):
    # Unit runs select `-k "not e2e"`; the e2e run selects `-k "e2e"` and
    # needs the real SDK for dispatch.put(). The beam TaskQueue decorator
    # prompts for a Token at import time, which has no TTY in CI.
    if (config.option.keyword or "").strip() != "e2e":
        _install_beam_stub()
