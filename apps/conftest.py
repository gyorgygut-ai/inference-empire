import sys
import types
from typing import Any
from urllib.parse import quote

import httpx
import pytest


class FakeR2Artifacts:
    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def put(self, key: str, body: bytes) -> None:
        self.objects[key] = body

    def presigned_url(self, key: str, expires: int = 3600) -> str:
        return f"https://fake-r2.local/{quote(key)}"

    def has(self, key: str) -> bool:
        return key in self.objects

    def fetch(self, key: str) -> bytes:
        return self.objects[key]


@pytest.fixture
def bucket():
    return FakeR2Artifacts()


def _artifact_exists(url: str, timeout: int = 30) -> bool:
    try:
        response = httpx.get(url, timeout=timeout)
        return response.status_code == 200 and len(response.content) > 0
    except httpx.HTTPError:
        return False


@pytest.fixture
def artifact_exists():
    return _artifact_exists


class _FluentMeta(type):
    def __getattr__(cls, name):
        return lambda *_, **__: _Fluent()


class _Fluent(metaclass=_FluentMeta):
    """Import-time stand-in for beam SDK builders (Image/Volume/Autoscaler)."""

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        return lambda *_, **__: self


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


def _asgi_stub(**kwargs):
    def deco(fn):
        return fn

    return deco


def _install_beam_stub():
    mod: Any = types.ModuleType("beam")
    mod.Image = _Fluent
    mod.QueueDepthAutoscaler = _Fluent
    mod.Volume = _Fluent
    mod.task_queue = _task_queue_stub
    mod.asgi = _asgi_stub
    sys.modules["beam"] = mod


def pytest_configure(config):
    # Unit runs select `-k "not e2e"`; the e2e run selects `-k "e2e"` and
    # needs the real SDK for dispatch.put(). The beam TaskQueue decorator
    # prompts for a Token at import time, which has no TTY in CI.
    if (config.option.keyword or "").strip() != "e2e":
        _install_beam_stub()
