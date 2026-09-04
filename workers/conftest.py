"""Single test harness for workers/. All machinery lives here.

Each test file imports its spec object
(`from workers.<model>.testing import <SPEC> as SPEC`); that import is the
only per-file wiring. Tests keep the identical triple
`(platform, runner, storage)` plus `platform.create_worker(storage)` +
`runner.run(worker, **inputs)`. `--target fake` (default) runs everything
mocked locally. `--target live` is owner-operated only and never executed
by this plan.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Callable

import pytest

from workers.services.platform.platform_factory import (
    beam_platform_factory,
    flash_platform_factory,
    modal_platform_factory,
)
from workers.services.runner.runner_factory import (
    beam_async_runner_factory,
    beam_sync_runner_factory,
    flash_async_runner_factory,
    flash_sync_runner_factory,
    modal_async_runner_factory,
    modal_sync_runner_factory,
)
from workers.services.storage.storage_factory import storage_factory

POLL_INTERVAL = 0.05


def pytest_addoption(parser):
    parser.addoption(
        "--target",
        action="store",
        default="fake",
        choices=("fake", "live"),
        help="fake = mocked locally (default); live = owner-operated dev run",
    )


@dataclass
class WorkerSpec:
    id: str
    provider: str  # flash | beam | modal
    kind: str  # sync | async
    shape: str  # flash_cls | flash_pre | flash_comfy | modal_cls | beam_tq | beam_eq | beam_comfy | beam_asgi | modal_asgi
    module: str
    attr: str  # class name or function name on the module
    method: str | None = None  # generate | analyze; None when attr IS the function
    loader_attr: str | None = None  # bare loader name for monkeypatch
    pipe_attrs: tuple = ()  # modal_cls: attr names injected from fake_builder()
    input_model: Any = None
    fake_builder: Callable | None = None  # loader fake / on_start value
    run_fake_name: str | None = None  # module attr holding run_*/analyze core
    run_fake: Callable | None = None  # canned replacement (no content inspection)
    live_endpoint: Any = None  # filled in Todo 5; None until then
    extra: dict = field(default_factory=dict)


class FakeCtx:
    """Attribute bag standing in for Beam's context (on_start_value)."""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def beam_unwrap(decorated):
    """Fake-path-only Beam bypass (pinned beam-client==0.2.207).

    TaskQueue/Endpoint/ASGI decorators wrap the function in
    `_CallableWrapper`, whose `__call__` raises locally ("Direct calls ...
    are not supported"). `.func` is the same method-body code — unwrap it.
    Breaks loudly on SDK upgrade, which is the desired tripwire.
    """
    from importlib.metadata import version

    assert version("beam-client") == "0.2.207", (
        f"beam bypass verified on 0.2.207, got {version('beam-client')}"
    )
    return getattr(decorated, "func", decorated)


@pytest.fixture(scope="session")
def target(request):
    return request.config.getoption("--target")


@pytest.fixture()
def spec(request):
    module_spec = getattr(request.module, "SPEC", None)
    assert module_spec is not None, (
        f"{request.module.__name__} must import its WorkerSpec as SPEC "
        "(from workers.<model>.testing import <SPEC> as SPEC)"
    )
    return module_spec


@pytest.fixture()
def storage(target):
    return storage_factory(target)


@pytest.fixture()
def platform(target, spec, monkeypatch):
    factory = {
        "flash": flash_platform_factory,
        "beam": beam_platform_factory,
        "modal": modal_platform_factory,
    }[spec.provider]
    plat = factory(target)
    plat._worker_factory = lambda storage: build_proxy(spec, target, storage, monkeypatch)
    plat._spec = spec  # real platforms resolve deploy targets from it; fakes ignore
    plat.deploy()
    yield plat
    plat.undeploy()


@pytest.fixture()
def runner(target, spec):
    factory = {
        ("flash", "sync"): flash_sync_runner_factory,
        ("flash", "async"): flash_async_runner_factory,
        ("beam", "sync"): beam_sync_runner_factory,
        ("beam", "async"): beam_async_runner_factory,
        ("modal", "sync"): modal_sync_runner_factory,
        ("modal", "async"): modal_async_runner_factory,
    }[(spec.provider, spec.kind)]
    return factory(target)


def build_proxy(spec, target, storage, monkeypatch):
    """Fake -> local proxy (stubbed backend, real logic). Live -> remote proxy."""
    if target == "live":
        return _LiveProxy(spec)
    mod = importlib.import_module(spec.module)
    if spec.shape in ("flash_cls", "flash_pre"):
        if spec.loader_attr:
            monkeypatch.setattr(mod, spec.loader_attr, spec.fake_builder)
        if spec.run_fake_name:
            monkeypatch.setattr(mod, spec.run_fake_name, spec.run_fake)
        return SimpleNamespace(generate=_flash_generate(spec, storage))
    if spec.shape == "modal_cls":
        if spec.loader_attr:
            monkeypatch.setattr(mod, spec.loader_attr, spec.fake_builder)
        if spec.run_fake_name:
            monkeypatch.setattr(mod, spec.run_fake_name, spec.run_fake)
        return SimpleNamespace(generate=_modal_generate(spec, storage))
    if spec.shape == "flash_comfy":
        return SimpleNamespace(generate=_flash_comfy_generate(spec, storage))
    if spec.shape == "beam_comfy":
        _patch_comfy_requests(mod, spec, monkeypatch)
        func = beam_unwrap(getattr(mod, spec.attr))
        return SimpleNamespace(
            generate=lambda **kw: func(
                FakeCtx(on_start_value=spec.fake_builder()), storage=storage, **kw
            )
        )
    if spec.shape in ("beam_tq", "beam_eq"):
        if spec.run_fake_name:
            monkeypatch.setattr(mod, spec.run_fake_name, spec.run_fake)
        func = beam_unwrap(getattr(mod, spec.attr))
        return SimpleNamespace(
            generate=lambda **kw: func(
                FakeCtx(on_start_value=spec.fake_builder()), storage=storage, **kw
            )
        )
    if spec.shape in ("beam_asgi", "modal_asgi"):
        return _voice_proxy(spec, monkeypatch)
    raise ValueError(f"unknown shape: {spec.shape!r}")


def _flash_generate(spec, storage):
    """Bypass runpod_flash RemoteClassWrapper dispatch.

    The decorated class dispatches methods remotely. `wrapper._class_type`
    is the original class (pinned runpod-flash==1.7.0): instantiate it
    directly and call the same method-body code. `load()`/`enter()` never
    run; the loader is monkeypatched to the fake.
    """
    mod = importlib.import_module(spec.module)
    wrapper_cls = getattr(mod, spec.attr)
    probe = wrapper_cls(storage=storage)
    orig = probe._class_type
    inst = orig.__new__(orig)
    orig.__init__(inst, storage=storage)

    def generate(**kw):
        return getattr(orig, spec.method)(inst, **kw)

    return generate


def _modal_generate(spec, storage):
    """Bypass Modal Cls dispatch + enter/load.

    Verified against pinned modal==1.5.5: direct calls raise
    `TypeError: 'Function' object is not callable`, and `.local()` runs
    `@modal.enter()` (boots real models — must never happen in fake).
    `_get_user_cls()` + `PartialFunction._get_raw_f()` reach the same
    method-body code. The instance is hand-built (`__new__` + storage and
    pipe attrs) mirroring what `__init__` + `load()` would set.
    """
    import modal

    assert modal.__version__ == "1.5.5", f"modal bypass verified on 1.5.5, got {modal.__version__}"
    mod = importlib.import_module(spec.module)
    user_cls = getattr(mod, spec.attr)._get_user_cls()
    raw = getattr(user_cls, spec.method)._get_raw_f()
    inst = user_cls.__new__(user_cls)
    inst.storage = storage
    for name, value in zip(spec.pipe_attrs, spec.fake_builder()):
        setattr(inst, name, value)

    def generate(**kw):
        return raw(inst, **kw)

    return generate


def _flash_comfy_generate(spec, storage):
    """Comfy flash: real worker, backend Endpoint swapped for the fake.

    The constructor's `Endpoint(...)` is network-inert until called; the
    fake replaces it post-construction. Same `generate` body executes.
    """
    mod = importlib.import_module(spec.module)
    wrapper_cls = getattr(mod, spec.attr)
    probe = wrapper_cls(storage=storage)
    orig = probe._class_type
    inst = orig.__new__(orig)
    orig.__init__(inst, storage=storage)
    inst.endpoint = spec.fake_builder()

    def generate(**kw):
        return orig.generate(inst, **kw)

    return generate


def _patch_comfy_requests(mod, spec, monkeypatch):
    """Comfy beam: canned `prompt_id` + history JSON + mp4 bytes."""
    canned_history, canned_mp4 = spec.fake_builder()

    class _Resp:
        def __init__(self, json_data=None, content=b"", status_code=200):
            self._json = json_data or {}
            self.content = content
            self.status_code = status_code

        def json(self):
            return self._json

        def raise_for_status(self):
            pass

    def fake_post(url, **kw):
        return _Resp(json_data={"prompt_id": "fake-prompt-id"})

    def fake_get(url, **kw):
        if "/history/" in url:
            return _Resp(json_data=canned_history)
        return _Resp(content=canned_mp4)

    monkeypatch.setattr(mod.requests, "post", fake_post)
    monkeypatch.setattr(mod.requests, "get", fake_get)


class _LiveProxy:
    """Placeholder until Todo 5 wires real provider calls. Never executed here."""

    def __init__(self, spec):
        self._spec = spec

    def generate(self, **inputs):
        raise NotImplementedError("live runner bodies land in Todo 5 (owner-operated)")


def _voice_proxy(spec, monkeypatch):
    """Stub `models` only; real app + real session logic still run."""
    from fastapi.testclient import TestClient

    app = spec.fake_builder(monkeypatch)
    client = TestClient(app)
    if spec.extra.get("voice_mode") == "rest":
        return SimpleNamespace(generate=_rest_generate(client))

    def generate(**kw):
        if isinstance(kw.get("type"), str) and "failure" in kw["type"]:
            raise RuntimeError("inference failed: canned failure")
        with client.websocket_connect("/v1/realtime") as ws:
            ws.send_json(
                {k: v for k, v in kw.items() if k in ("type", "session", "audio")}
            )
            return ws.receive_json()

    return SimpleNamespace(generate=generate)


def _rest_generate(client):
    def generate(**kw):
        if isinstance(kw.get("type"), str) and "failure" in kw["type"]:
            raise RuntimeError("inference failed: canned failure")
        body = kw.get("body", {"model": "x", "input": "hello", "voice": "GutAI"})
        path = kw.get("path", "/v1/audio/speech")
        resp = client.post(path, json=body)
        return {
            "status_code": resp.status_code,
            "content_type": resp.headers.get("content-type"),
            "content_len": len(resp.content),
        }

    return generate


def fake_png() -> bytes:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


def fake_mp4_stub() -> bytes:
    return b"\x00\x00\x00 ftypmp42" + b"\x00" * 256
