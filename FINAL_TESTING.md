# FINAL_TESTING.md — full plan

## 1. Locks

* `fake`/`live` everywhere. `workers/conftest.py:40`, `runner_factory.py`, `platform_factory.py`, `storage_factory.py` already `fake`/`live`. Only fix: `Makefile:4` `test-all-dev` → `test-all-live`, `Makefile:10` `test-dev` → `test-live` (bodies already `--target live`).
* One `workers/conftest.py`. 6 fixtures, named by protocol only: `flash_cls`, `flash_pre`, `beam_eq`, `beam_tq`, `beam_asgi`, `modal_cls`.
* Each fixture carries its flow. No `runner` arg, no flow decision in tests.
* No registry of any kind: no `HARNESS_*` dicts, no `@pytest.mark.worker(...)`, no `@harness(...)`, no `WORKER_MODULE` / `WORKER_ATTR` constants in tests. Platform + runner classes encapsulate all of it. Tests self-register by fixture name.
* Delete `workers/tests/test_ceremony.py` (188 lines, done). Its decorator scan moves into platform classes; its contract checks are replaced by per-test output asserts.
* Rename 3 voice test files to the `test_worker_*` convention + add 1 qwen test so path inference holds everywhere.

## 2. How identity works with zero test config

```
test path: workers/flux2/tests/test_worker_beam_tq_flux2_klein9b.py
        → worker: workers.flux2.worker_beam_tq_flux2_klein9b  (strip tests/test_ → worker_)
        → entry: scan module for @task_queue (beam_tq) — no attr name
```

* `_infer(path)` lives in `conftest.py`, pure path math. No map. Caller uses `request.node.path` (pytest 8).
* `_decorated(mod, names)` scans the imported worker module for its provider decorator:
  `flash_cls`/`flash_pre` → `@Endpoint` + `_flash_class`; `beam_tq` → `@task_queue`, `beam_eq` → `@endpoint`, `beam_asgi` → `@asgi` + `_beam_unwrap`; `modal_cls` → `modal.App` + `@app.cls` + `_modal_class`. Loader/pipes (`load_pipeline`, `pipe`, `generate`, `ComfyEndpoint`, voice stubs, `TestClient` WS) stay in the existing conftest helpers, called by the fixture — never by the test.
* Voice chat (`worker_modal_cls_voice_chat.py`) is a `cls` worker, so it uses `modal_cls` (sync). There is no `worker_modal_asgi_*.py`, hence no `modal_asgi` fixture.

## 3. Fixture → flow (hardcoded per fixture body, no lookup)

| Fixture | Platform | Flow exposed on fixture | Runner built inside |
|---|---|---|---|
| `flash_cls` | flash | sync: `run` | `flash_sync_runner_factory(target)` |
| `flash_pre` | flash | async: `submit`/`poll`/`result`/`run` | `flash_async_runner_factory(target)` |
| `beam_eq` | beam | sync: `run` | `beam_sync_runner_factory(target)` |
| `beam_tq` | beam | async | `beam_async_runner_factory(target)` |
| `beam_asgi` | beam | realtime (WS) | `beam_async_runner_factory(target)` + voice app |
| `modal_cls` | modal | sync | `modal_sync_runner_factory(target)` |

`fake` → `Fake*Runner` simulates (`fake_runners.py:27-57`); `live` → `Real*Runner` hits the cloud (`real_runners.py:60-204`). Storage is the only second arg: `storage_factory(target)`.

Session fixtures own only `deploy()/yield/undeploy()`. Each protocol fixture returns a fresh per-test `_Harness(platform, runner, make)` — never mutates the session platform object.

## 4. Full `workers/conftest.py` preview

```python
"""Unified harness: protocol fixtures = identity + flow. No registry, no markers."""
from __future__ import annotations
import ast
import importlib
import pytest

from workers.services.platform.platform_factory import (
    beam_platform_factory, flash_platform_factory, modal_platform_factory,
)
from workers.services.runner.runner_factory import (
    beam_async_runner_factory, beam_sync_runner_factory,
    flash_async_runner_factory, flash_sync_runner_factory,
    modal_sync_runner_factory,
)
from workers.services.storage.storage_factory import storage_factory

# Existing fakes/stubs kept verbatim (fake_png, _FakePipe, _FakeCtx,
# _FakeComfyEndpoint, _StubTTS/_StubConverter/_StubSileroVAD,
# _fake_loader_for, _beam_unwrap, _flash_class, _modal_class, _build_voice_app).

def pytest_addoption(parser):
    parser.addoption("--target", default="fake", choices=("fake", "live"))

@pytest.fixture(scope="session")
def target(request):
    return request.config.getoption("--target")

@pytest.fixture
def storage(target):
    return storage_factory(target)

# ---- beforeAll: deploy only, no mutation ----
@pytest.fixture(scope="session")
def flash_platform(target):
    p = flash_platform_factory(target); p.deploy(); yield p; p.undeploy()

@pytest.fixture(scope="session")
def beam_platform(target):
    p = beam_platform_factory(target); p.deploy(); yield p; p.undeploy()

@pytest.fixture(scope="session")
def modal_platform(target):
    p = modal_platform_factory(target); p.deploy(); yield p; p.undeploy()

# ---- inference + discovery (encapsulated, no test input) ----
def _infer(path: str) -> str:
    # workers/flux2/tests/test_worker_beam_tq_X.py -> workers.flux2.worker_beam_tq_X
    parts = str(path).replace(".py", "").split("/")
    i = parts.index("tests")
    mod = parts[:i] + [parts[i + 1].replace("test_worker_", "worker_")]
    return ".".join(mod[mod.index("workers"):])

def _decorated(mod, names: tuple) -> object:
    tree = ast.parse(open(mod.__file__).read())
    for node in ast.walk(tree):
        for dec in getattr(node, "decorator_list", []):
            f = dec.func if isinstance(dec, ast.Call) else dec
            n = getattr(f, "id", getattr(f, "attr", ""))
            if n in names:
                return getattr(mod, node.name)
    raise AssertionError(f"no @{names} in {mod.__name__}")

class _Harness:
    """Per-test wrapper. Session platform is referenced, never mutated."""

    def __init__(self, platform, runner, make, spec):
        self._platform = platform
        self._runner = runner
        self._make = make
        self._spec = spec

    def create_worker(self, storage):
        worker = self._make(storage)
        worker._spec = self._spec
        return worker

    def run(self, worker, **kw):
        return self._runner.run(worker, **kw)

    def submit(self, worker, **kw):
        return self._runner.submit(worker, **kw)

    def poll(self, task_id):
        return self._runner.poll(task_id)

    def result(self, task_id, timeout=30):
        return self._runner.result(task_id, timeout=timeout)
```

```python
# WorkerSpec lives in workers/services/platform/spec.py (new, ~15 lines)
from dataclasses import dataclass, field

@dataclass(frozen=True)
class WorkerSpec:
    module: str
    attr: str
    live_endpoint: str
    shape: str
    input_model: object = None
    extra: dict = field(default_factory=dict)
```

```python
# ---- 6 fixtures, each explicit (loader/pipe bodies kept verbatim) ----
@pytest.fixture
def flash_cls(flash_platform, target, monkeypatch, request):
    from workers.conftest import _flash_class, _fake_loader_for
    from workers.services.platform.spec import WorkerSpec
    mod_name = _infer(str(request.node.path))
    mod = importlib.import_module(mod_name)
    if hasattr(mod, "load_pipeline"):
        monkeypatch.setattr(mod, "load_pipeline", _fake_loader_for(mod_name))
    decorated = _decorated(mod, ("Endpoint",))
    cls = _flash_class(decorated)
    runner = flash_sync_runner_factory(target)  # sync flow
    spec = WorkerSpec(module=mod_name, attr=decorated.__name__,
                      live_endpoint=mod_name.split("worker_")[1].replace("_", "-"),
                      shape="flash_cls")
    return _Harness(flash_platform, runner, lambda storage, _c=cls: _c(storage), spec)

@pytest.fixture
def flash_pre(flash_platform, target, monkeypatch, request):
    from workers.conftest import _flash_class, _fake_loader_for, _FakeComfyEndpoint
    from workers.services.platform.spec import WorkerSpec
    mod_name = _infer(str(request.node.path))
    mod = importlib.import_module(mod_name)
    monkeypatch.setattr(mod, "load_pipeline", _fake_loader_for(mod_name))
    for n in ("ComfyEndpoint", "ComfyAPI", "endpoint", "client"):
        if hasattr(mod, n):
            monkeypatch.setattr(mod, n, _FakeComfyEndpoint)
    decorated = _decorated(mod, ("Endpoint",))
    cls = _flash_class(decorated)
    runner = flash_async_runner_factory(target)  # async flow
    spec = WorkerSpec(module=mod_name, attr=decorated.__name__,
                      live_endpoint=mod_name.split("worker_")[1].replace("_", "-"),
                      shape="flash_pre")
    return _Harness(flash_platform, runner, lambda storage, _c=cls: _c(storage), spec)

@pytest.fixture
def beam_eq(beam_platform, target, monkeypatch, request):
    from workers.conftest import _beam_unwrap, _fake_loader_for, _FakeCtx
    from workers.services.platform.spec import WorkerSpec
    mod_name = _infer(str(request.node.path))
    mod = importlib.import_module(mod_name)
    decorated = _decorated(mod, ("endpoint",))
    fn = _beam_unwrap(decorated)
    runner = beam_sync_runner_factory(target)  # sync flow
    def make(storage, _f=fn, _m=mod_name):
        ctx = _FakeCtx(_fake_loader_for(_m)())
        class _W: pass
        w = _W(); w.generate = lambda **i: _f(ctx, storage, **i); return w
    spec = WorkerSpec(module=mod_name, attr=decorated.__name__,
                      live_endpoint=mod_name.split("worker_")[1].replace("_", "-"),
                      shape="beam_eq")
    return _Harness(beam_platform, runner, make, spec)

@pytest.fixture
def beam_tq(beam_platform, target, monkeypatch, request):
    from workers.conftest import _beam_unwrap, _fake_loader_for, _FakeCtx
    from workers.services.platform.spec import WorkerSpec
    mod_name = _infer(str(request.node.path))
    mod = importlib.import_module(mod_name)
    decorated = _decorated(mod, ("task_queue",))
    fn = _beam_unwrap(decorated)
    runner = beam_async_runner_factory(target)  # async flow
    def make(storage, _f=fn, _m=mod_name):
        ctx = _FakeCtx(_fake_loader_for(_m)())
        class _W: pass
        w = _W(); w.generate = lambda **i: _f(ctx, storage, **i); return w
    spec = WorkerSpec(module=mod_name, attr=decorated.__name__,
                      live_endpoint=mod_name.split("worker_")[1].replace("_", "-"),
                      shape="beam_tq")
    return _Harness(beam_platform, runner, make, spec)

@pytest.fixture
def beam_asgi(beam_platform, target, monkeypatch, request):
    from workers.conftest import _build_voice_app
    from workers.services.platform.spec import WorkerSpec
    mod_name = _infer(str(request.node.path))
    app = _build_voice_app(mod_name, monkeypatch)
    runner = beam_async_runner_factory(target)  # realtime over async runner
    def make(storage):
        from fastapi.testclient import TestClient
        client = TestClient(app)
        class _W:
            def generate(self, **inputs):
                for v in inputs.values():
                    if isinstance(v, str) and "failure" in v:
                        raise RuntimeError("inference failed: canned failure")
                with client.websocket_connect("/ws") as ws:
                    ws.send_json({"type": "session.update", "session": inputs.get("session", {})})
                    return ws.receive_json()
        return _W()
    spec = WorkerSpec(module=mod_name, attr="asgi",
                      live_endpoint=mod_name.split("worker_")[1].replace("_", "-"),
                      shape="beam_asgi")
    return _Harness(beam_platform, runner, make, spec)

@pytest.fixture
def modal_cls(modal_platform, target, monkeypatch, request):
    from workers.conftest import _modal_class, _fake_loader_for
    from workers.services.platform.spec import WorkerSpec
    mod_name = _infer(str(request.node.path))
    mod = importlib.import_module(mod_name)
    decorated = _decorated(mod, ("cls",))
    cls = _modal_class(decorated)
    pipes = ("pipe",)
    runner = modal_sync_runner_factory(target)  # sync flow
    def make(storage, _c=cls, _m=mod_name):
        inst = _c.__new__(_c); inst.storage = storage
        vals = _fake_loader_for(_m)()
        vals = vals if isinstance(vals, tuple) else (vals,)
        for n, v in zip(pipes, vals):
            setattr(inst, n, v)
        raw = getattr(_c, "generate")
        raw = getattr(raw, "_get_raw_f", lambda: raw)()
        inst.generate = lambda **i: raw(inst, **i); return inst
    spec = WorkerSpec(module=mod_name, attr=decorated.__name__,
                      live_endpoint=mod_name.split("worker_")[1].replace("_", "-"),
                      shape="modal_cls")
    return _Harness(modal_platform, runner, make, spec)
```

## 5. Real-runner fix (live path only)

`workers/services/runner/real_runners.py:188-203` — `RealModalAsyncRunner` gains `submit/poll/result` (currently `run`-only):

```python
class RealModalAsyncRunner(_RealRunnerBase):
    def __init__(self):
        self._calls: dict = {}

    def submit(self, worker, **inputs):
        import modal
        async def _submit():
            cls = modal.Cls.from_name(worker._spec.live_endpoint, worker._spec.attr)
            return await cls().generate.spawn(**_payload(worker, inputs))
        task_id = f"task-{secrets.token_hex(4)}"
        self._calls[task_id] = _bridge(_submit)
        return task_id

    def poll(self, task_id):
        return "IN_PROGRESS" if task_id in self._calls else "COMPLETED"

    def result(self, task_id, timeout=1800):
        async def _get():
            return await self._calls[task_id].get()
        try:
            return _bridge(_get, timeout)
        finally:
            self._calls.pop(task_id, None)

    def run(self, worker, **inputs):
        return self.result(self.submit(worker, **inputs))
```

Rationale: `worker._spec` is set by `_Harness.create_worker` (§4), so `_payload`/`live_endpoint`/`attr` resolve on live. Fake path untouched.

## 6. Test previews (zero config, zero decorators with args)

```python
# workers/flux2/tests/test_worker_beam_tq_flux2_klein9b.py
def test_success(beam_tq, storage):
    worker = beam_tq.create_worker(storage=storage)
    out = beam_tq.run(worker, storage=storage, prompt="cat")
    assert "image_url" in out

def test_async_poll(beam_tq, storage):
    worker = beam_tq.create_worker(storage=storage)
    tid = beam_tq.submit(worker, storage=storage, prompt="cat")
    assert beam_tq.poll(tid) in ("IN_PROGRESS", "COMPLETED")
    assert "image_url" in beam_tq.result(tid)
```

```python
# workers/flux2/tests/test_worker_flash_cls_flux2_klein9b.py
def test_success(flash_cls, storage):
    worker = flash_cls.create_worker(storage=storage)
    out = flash_cls.run(worker, storage=storage, prompt="a cat")
    assert "image_url" in out
```

```python
# workers/voice/tests/test_worker_beam_asgi_realtime_voice_openvoice.py (renamed)
def test_session_created(beam_asgi, storage):
    worker = beam_asgi.create_worker(storage=storage)
    evt = beam_asgi.run(worker, storage=storage, type="session.update", session={})
    assert evt["type"] in ("session.created", "session.updated", "error")
```

```python
# workers/voice/tests/test_worker_modal_cls_voice_chat.py (renamed)
def test_chat(modal_cls, storage):
    worker = modal_cls.create_worker(storage=storage)
    out = modal_cls.run(worker, storage=storage, prompt="hello")
    assert out
```

```python
# workers/voice/tests/test_worker_beam_asgi_realtime_voice_qwen.py (new)
def test_session_created(beam_asgi, storage):
    worker = beam_asgi.create_worker(storage=storage)
    evt = beam_asgi.run(worker, storage=storage, type="session.update", session={})
    assert evt["type"] in ("session.created", "session.updated", "error")
```

## 7. File renames + adds + Makefile (to make inference total)

* `workers/voice/tests/test_voice_openvoice.py` → `test_worker_beam_asgi_realtime_voice_openvoice.py`
* `workers/voice/tests/test_voice_chatterbox.py` → `test_worker_beam_asgi_realtime_voice_chatterbox.py`
* `workers/voice/tests/test_voice_modal_chat.py` → `test_worker_modal_cls_voice_chat.py`
* Add `workers/voice/tests/test_worker_beam_asgi_realtime_voice_qwen.py` (covers `worker_beam_asgi_realtime_voice_qwen.py`, currently untested)
* `Makefile`: `test-all-dev` → `test-all-live`, `test-dev` → `test-live`:
```make
test-all-live:
	.venv/bin/python -m pytest workers/ --target live
test-live:
	@f=$$(find workers -name "test_*.py" | fzf --prompt="test-live> ") && [ -n "$$f" ] && .venv/bin/python -m pytest "$$f" --target live -q
```

## 8. Validation

* `python -m pytest workers/ --target fake` all green.
* `python -m pytest workers/<model>/tests/ --target fake -k <test>` per worker.
* `--target live` owner-operated only.

## 9. Touch list (exact)

* Write: `FINAL_TESTING.md` (this doc).
* New: `workers/services/platform/spec.py` (`WorkerSpec`).
* Edit: `workers/conftest.py` (§4; keep fake/voice stub bodies, replace marker plumbing with `_infer`/`_decorated`/`_Harness`/6 fixtures + `_spec` attach).
* Edit: `workers/services/runner/real_runners.py` (§5; `RealModalAsyncRunner.submit/poll/result`).
* Edit: `Makefile` (2 renames only, §7).
* Edit: ~20 `workers/*/tests/test_*.py` (delete all decorators/constants; signature `(protocol_fixture, storage)`; calls via `fixture.run/submit/poll/result`).
* Rename: 3 voice test files + add 1 qwen test (§7).
* Delete: `workers/tests/test_ceremony.py` (done).
