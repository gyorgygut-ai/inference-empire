"""Locked harness: 7 fixtures, per provider x protocol x sync/async.

No registry, no dict, no testing.py. Each fixture takes the `target` arg
only, builds its platform strictly via factories, deploy() in beforeAll,
yield, undeploy(). beforeEach (test body) builds runner + storage strictly
via factories and invokes run() on the received runner:

    runner = flash_sync_runner_factory(target)
    storage = storage_factory(target)
    worker = <fixture>.create_worker(storage=storage)
    runner.run(worker, storage=storage, **inputs)
"""

from __future__ import annotations

import importlib
import io
import struct
import sys
import types

import pytest

from workers.services.platform.platform_factory import (
    beam_platform_factory,
    flash_platform_factory,
    modal_platform_factory,
)
from workers.services.runner.runner_factory import (
    beam_async_runner_factory,
    flash_async_runner_factory,
    flash_sync_runner_factory,
    modal_async_runner_factory,
    modal_sync_runner_factory,
)
from workers.services.storage.storage_factory import storage_factory  # noqa: F401  (beforeEach use)


def pytest_addoption(parser):
    parser.addoption("--target", default="fake", choices=("fake", "live"))


@pytest.fixture(scope="session")
def target(request):
    return request.config.getoption("--target")


def _kw(request):
    marker = request.node.get_closest_marker("worker")
    assert marker is not None, "test needs @pytest.mark.worker(...)"
    return marker.kwargs


def fake_png() -> bytes:
    import PIL.Image

    buf = io.BytesIO()
    PIL.Image.new("RGB", (8, 8), (1, 2, 3)).save(buf, format="PNG")
    return buf.getvalue()


def fake_mp4_stub() -> bytes:
    return b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64


class _FakeMod:
    pass


class _FakePipe:
    """Canned pipe: __call__ returns object with .images/.frames for save."""

    def __init__(self, png: bytes):
        self._png = png

    def __call__(self, *a, **k):
        import PIL.Image

        class _Out:
            pass

        out = _Out()
        img = PIL.Image.open(io.BytesIO(self._png))
        out.images = [img]
        out.frames = [[img]]
        return out


class _FakeCtx:
    def __init__(self, on_start_value):
        self.on_start_value = on_start_value


def _fake_loader_for(module_name: str):
    png = fake_png()

    def _fake(*a, **k):
        return _FakePipe(png), _FakeMod()

    return _fake


class _FakeComfyEndpoint:
    def __init__(self, *a, **k):
        pass

    def queue_prompt(self, *a, **k):
        return {"prompt_id": "fake-prompt-id"}

    def get_history(self, *a, **k):
        return {}

    def get_image(self, *a, **k):
        return fake_png()

    def get_video(self, *a, **k):
        return fake_mp4_stub()


def _beam_unwrap(decorated):
    return getattr(decorated, "func", decorated)


def _flash_class(decorated):
    for attr in ("_class_type", "__wrapped__", "cls", "_cls"):
        obj = getattr(decorated, attr, None)
        if isinstance(obj, type):
            return obj
    raise TypeError(f"cannot unwrap flash endpoint {decorated!r}")


def _modal_class(decorated):
    get_user_cls = getattr(decorated, "_get_user_cls", None)
    if callable(get_user_cls):
        return get_user_cls()
    raw = getattr(decorated, "_get_raw_f", None)
    if callable(raw):
        fn = raw()
        return getattr(fn, "__self__", None).__class__ if hasattr(fn, "__self__") else fn
    for attr in ("__wrapped__", "cls", "_cls"):
        obj = getattr(decorated, attr, None)
        if isinstance(obj, type):
            return obj
    raise TypeError(f"cannot unwrap modal cls {decorated!r}")


def _proxy_factory(kw, monkeypatch):
    """Build worker_factory(storage) -> object with .generate(**inputs)."""
    module = importlib.import_module(kw["module"])
    protocol = kw["protocol"]
    loader_name = kw.get("loader")

    if loader_name:
        monkeypatch.setattr(module, loader_name, _fake_loader_for(kw["module"]))
    if protocol in ("flash_pre", "beam_tq") and "comfy" in kw["module"]:
        for name in ("ComfyEndpoint", "ComfyAPI", "endpoint", "client"):
            if hasattr(module, name):
                monkeypatch.setattr(module, name, _FakeComfyEndpoint)

    if protocol in ("flash_cls", "flash_pre"):
        cls = _flash_class(getattr(module, kw["attr"]))

        def make(storage, _cls=cls):
            return _cls(storage)

        return make

    if protocol in ("beam_tq", "beam_eq"):
        fn = _beam_unwrap(getattr(module, kw["attr"]))
        method = kw.get("method", "generate")

        def make(storage, _fn=fn):
            ctx = _FakeCtx(_fake_loader_for(kw["module"])())

            class _W:
                pass

            w = _W()
            if method == "generate":
                w.generate = lambda **inputs: _fn(ctx, storage, **inputs)
            else:
                inner = getattr(_fn, method, _fn)
                w.generate = lambda **inputs: inner(ctx, storage, **inputs)
            return w

        return make

    if protocol == "modal_cls":
        cls = _modal_class(getattr(module, kw["attr"]))
        pipes = tuple(kw.get("pipes", ("pipe",)))

        def make(storage, _cls=cls):
            inst = _cls.__new__(_cls)
            inst.storage = storage
            vals = _fake_loader_for(kw["module"])()
            if not isinstance(vals, tuple):
                vals = (vals,)
            for name, val in zip(pipes, vals):
                setattr(inst, name, val)
            raw_generate = getattr(_cls, kw.get("method", "generate"))
            raw_generate = getattr(raw_generate, "_get_raw_f", lambda: raw_generate)()
            inst.generate = lambda **inputs: raw_generate(inst, **inputs)
            return inst

        return make

    if protocol == "beam_asgi":
        app = _build_voice_app(kw["module"], monkeypatch)

        def make(storage):
            from fastapi.testclient import TestClient

            client = TestClient(app)

            class _W:
                def generate(self, **inputs):
                    if inputs.get("type") == "failure" or any(
                        isinstance(v, str) and "failure" in v for v in inputs.values()
                    ):
                        raise RuntimeError("inference failed: canned failure")
                    with client.websocket_connect("/ws") as ws:
                        ws.send_json({"type": "session.update", "session": inputs.get("session", {})})
                        return ws.receive_json()

            return _W()

        return make

    if protocol == "modal_asgi":
        fn = getattr(importlib.import_module(kw["module"]), kw["attr"])
        raw = getattr(fn, "_get_raw_f", lambda: fn)()

        def make(storage):
            app = raw(None) if callable(raw) else raw
            from fastapi.testclient import TestClient

            client = TestClient(app)

            class _W:
                def generate(self, **inputs):
                    if inputs.get("type") == "failure" or any(
                        isinstance(v, str) and "failure" in v for v in inputs.values()
                    ):
                        raise RuntimeError("inference failed: canned failure")
                    with client.websocket_connect("/ws") as ws:
                        ws.send_json({"type": "session.update", "session": inputs.get("session", {})})
                        return ws.receive_json()

            return _W()

        return make

    raise ValueError(f"unknown protocol: {protocol!r}"


# ---- voice stubs (beam_asgi / modal_asgi only) ----


class _StubTTS:
    def __init__(self, *a, **k):
        pass

    def infer(self, *a, **k):
        return b"\x00\x00" * 160


class _StubConverter:
    def __init__(self, *a, **k):
        pass

    def convert(self, *a, **k):
        return b"\x00\x00" * 160


class _StubSileroVAD:
    def __init__(self, *a, **k):
        pass

    def __call__(self, *a, **k):
        return {"speech": True}


def _resample_pcm16(pcm: bytes, src: int, dst: int) -> bytes:
    if src == dst:
        return pcm
    n = len(pcm) // 2
    if n == 0:
        return b""
    src_samples = struct.unpack(f"<{n}h", pcm)
    ratio = src / dst
    out_n = max(1, int(n / ratio))
    idx = [min(n - 1, int(i * ratio)) for i in range(out_n)]
    return struct.pack(f"<{out_n}h", *(src_samples[i] for i in idx))


def _stub_module(name: str, **attrs) -> types.ModuleType:
    mod = types.ModuleType(name)
    for key, val in attrs.items():
        setattr(mod, key, val)
    sys.modules[name] = mod
    return mod


def _build_voice_app(module_name: str, monkeypatch):
    _stub_module("chatterbox_tts", ChatterboxTTS=_StubTTS)
    _stub_module("openvoice_converter", ToneConverter=_StubConverter)
    _stub_module("silero_vad", SileroVAD=_StubSileroVAD)
    fake_event = types.ModuleType("realtime_protocol")
    fake_event.FakeEvent = dict
    sys.modules["realtime_protocol"] = fake_event
    module = importlib.import_module(module_name)
    builder = getattr(module, "app", None) or getattr(module, "build_app", None) or getattr(module, "worker")
    app = builder() if callable(builder) else builder
    return app


# ---- locked 7: per provider x protocol x sync/async ----


@pytest.fixture
def flash_cls_sync_worker(target, monkeypatch, request):
    kw = _kw(request)
    assert (kw["provider"], kw["protocol"]) == ("flash", "flash_cls")
    platform = flash_platform_factory(target)
    platform._worker_factory = _proxy_factory(kw, monkeypatch)
    platform.deploy()
    yield platform
    platform.undeploy()


@pytest.fixture
def flash_pre_async_worker(target, monkeypatch, request):
    kw = _kw(request)
    assert (kw["provider"], kw["protocol"]) == ("flash", "flash_pre")
    platform = flash_platform_factory(target)
    platform._worker_factory = _proxy_factory(kw, monkeypatch)
    platform.deploy()
    yield platform
    platform.undeploy()


@pytest.fixture
def beam_tq_async_worker(target, monkeypatch, request):
    kw = _kw(request)
    assert (kw["provider"], kw["protocol"]) == ("beam", "beam_tq")
    platform = beam_platform_factory(target)
    platform._worker_factory = _proxy_factory(kw, monkeypatch)
    platform.deploy()
    yield platform
    platform.undeploy()


@pytest.fixture
def beam_eq_async_worker(target, monkeypatch, request):
    kw = _kw(request)
    assert (kw["provider"], kw["protocol"]) == ("beam", "beam_eq")
    platform = beam_platform_factory(target)
    platform._worker_factory = _proxy_factory(kw, monkeypatch)
    platform.deploy()
    yield platform
    platform.undeploy()


@pytest.fixture
def beam_asgi_async_worker(target, monkeypatch, request):
    kw = _kw(request)
    assert (kw["provider"], kw["protocol"]) == ("beam", "beam_asgi")
    platform = beam_platform_factory(target)
    platform._worker_factory = _proxy_factory(kw, monkeypatch)
    platform.deploy()
    yield platform
    platform.undeploy()


@pytest.fixture
def modal_cls_sync_worker(target, monkeypatch, request):
    kw = _kw(request)
    assert (kw["provider"], kw["protocol"]) == ("modal", "modal_cls")
    platform = modal_platform_factory(target)
    platform._worker_factory = _proxy_factory(kw, monkeypatch)
    platform.deploy()
    yield platform
    platform.undeploy()


@pytest.fixture
def modal_asgi_async_worker(target, monkeypatch, request):
    kw = _kw(request)
    assert (kw["provider"], kw["protocol"]) == ("modal", "modal_asgi")
    platform = modal_platform_factory(target)
    platform._worker_factory = _proxy_factory(kw, monkeypatch)
    platform.deploy()
    yield platform
    platform.undeploy()
