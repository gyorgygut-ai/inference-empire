"""Unified harness: protocol fixtures = identity + flow. No registry, no markers."""

from __future__ import annotations

import ast
import base64
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
from workers.services.platform.spec import WorkerSpec
from workers.services.runner.runner_factory import (
    beam_async_runner_factory,
    beam_sync_runner_factory,
    flash_async_runner_factory,
    flash_sync_runner_factory,
    modal_sync_runner_factory,
)
from workers.services.storage.storage_factory import storage_factory


def pytest_addoption(parser):
    parser.addoption("--target", default="fake", choices=("fake", "live"))


@pytest.fixture(scope="session")
def target(request):
    return request.config.getoption("--target")


@pytest.fixture
def storage(target):
    return storage_factory(target)


@pytest.fixture(scope="session")
def flash_platform(target):
    p = flash_platform_factory(target)
    p.deploy()
    yield p
    p.undeploy()


@pytest.fixture(scope="session")
def beam_platform(target):
    p = beam_platform_factory(target)
    p.deploy()
    yield p
    p.undeploy()


@pytest.fixture(scope="session")
def modal_platform(target):
    p = modal_platform_factory(target)
    p.deploy()
    yield p
    p.undeploy()


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

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return lambda *a, **k: None


class _FakeH3Pipe:
    """Canned h3 pipe: __call__ returns (video, audio) tuple."""

    def __call__(self, *a, **k):
        class _Video:
            shape = (1, 8, 256, 256, 3)

        class _AudioVAE:
            sample_rate = 24000

        self.audio_vae = _AudioVAE()
        return _Video(), b"\x00" * 160


def _fake_write_video_audio(video, audio, output_path, fps=None, audio_sample_rate=None, **k):
    with open(output_path, "wb") as fh:
        fh.write(fake_mp4_stub())


class _FakeCtx:
    def __init__(self, on_start_value):
        self.on_start_value = on_start_value


def _fake_loader_for(module_name: str):
    png = fake_png()

    def _fake(*a, **k):
        return _FakePipe(png), _FakeMod()

    return _fake


def _fake_h3_loader_for(module_name: str):
    def _fake(*a, **k):
        return _FakeH3Pipe(), _fake_write_video_audio

    return _fake


def _fake_krea2_loader_for(module_name: str):
    png = fake_png()

    def _fake(*a, **k):
        return _FakePipe(png), "/tmp", _FakeMod()

    return _fake


def _canned_vision_analyze(*a, **k):
    return {"classification": "object_0p", "subjects": [], "description": "fake"}


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


class _FakeFlashEndpoint:
    """Fake runpod_flash.Endpoint for comfy workers: runsync -> canned job."""

    def __init__(self, *a, **k):
        pass

    async def runsync(self, payload, timeout=1800):
        data = base64.b64encode(fake_mp4_stub()).decode()

        class _Job:
            error = None
            output = {"images": [{"data": data}]}

        return _Job()


def _beam_unwrap(decorated):
    return getattr(decorated, "func", decorated)


def _flash_class(decorated):
    for attr in ("_class_type", "__wrapped__", "cls", "_cls"):
        obj = getattr(decorated, attr, None)
        if isinstance(obj, type):
            return obj
    # runpod_flash>=1.7 RemoteClassWrapper: user class lives in __init__ closure.
    init = getattr(decorated, "__init__", None)
    closure = getattr(init, "__closure__", None) or ()
    for cell in closure:
        try:
            val = cell.cell_contents
        except ValueError:
            continue
        if isinstance(val, type) and getattr(val, "__module__", "").startswith("workers"):
            return val
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


# ---- voice stubs (beam_asgi only) ----


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


# ---- inference + discovery (encapsulated, no test input) ----


def _infer(path: str) -> str:
    # workers/flux2/tests/test_worker_beam_tq_X.py -> workers.flux2.worker_beam_tq_X
    parts = str(path).replace(".py", "").split("/")
    i = parts.index("tests")
    mod = parts[:i] + [parts[i + 1].replace("test_worker_", "worker_")]
    return ".".join(mod[mod.index("workers") :])


def _decorated(mod, names: tuple) -> tuple:
    """Return (node_name, object) for the first def/class with a matching decorator."""
    tree = ast.parse(open(mod.__file__).read())
    for node in ast.walk(tree):
        for dec in getattr(node, "decorator_list", []):
            f = dec.func if isinstance(dec, ast.Call) else dec
            n = getattr(f, "id", getattr(f, "attr", ""))
            if n in names:
                return node.name, getattr(mod, node.name)
    raise AssertionError(f"no @{names} in {mod.__name__}")


def _live_endpoint_for(mod_name: str) -> str:
    return mod_name.split("worker_")[1].replace("_", "-")


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


def _patch_vision(mod, monkeypatch):
    monkeypatch.setattr(mod, "run_analyze", _canned_vision_analyze)
    if hasattr(mod, "load_models_as_needed"):
        monkeypatch.setattr(mod, "load_models_as_needed", lambda *a, **k: (object(), object(), "fake"))
    if hasattr(mod, "load_models"):
        monkeypatch.setattr(mod, "load_models", lambda *a, **k: (object(), object(), "fake"))


def _fake_vision_ctx():
    return (object(), object(), "fake")


class _FakeComfyRequests:
    @staticmethod
    def post(url, json=None, timeout=None, **k):
        class _R:
            def raise_for_status(self):
                pass

            def json(self):
                return {"prompt_id": "fake-prompt-id"}

        return _R()

    @staticmethod
    def get(url, timeout=None, **k):
        class _R:
            status_code = 200
            content = fake_mp4_stub()

            def json(self):
                return {
                    "fake-prompt-id": {
                        "outputs": {
                            "save": {
                                "videos": [{"filename": "f.mp4", "subfolder": "", "type": "output"}]
                            }
                        }
                    }
                }

        return _R()


def _patch_beam_comfy(mod, monkeypatch):
    monkeypatch.setattr(mod, "requests", _FakeComfyRequests, raising=False)


def _patch_comfy(mod, monkeypatch):
    for n in ("ComfyEndpoint", "ComfyAPI", "endpoint", "client"):
        if hasattr(mod, n):
            monkeypatch.setattr(mod, n, _FakeComfyEndpoint)
    try:
        import runpod_flash

        monkeypatch.setattr(runpod_flash, "Endpoint", _FakeFlashEndpoint, raising=False)
    except Exception:
        pass
    monkeypatch.setattr(mod, "Endpoint", _FakeFlashEndpoint, raising=False)


def _patch_krea2_loader(mod, monkeypatch, mod_name):
    if hasattr(mod, "load_pipeline_as_needed"):
        monkeypatch.setattr(mod, "load_pipeline_as_needed", _fake_krea2_loader_for(mod_name))


def _patch_h3_loader(mod, monkeypatch, mod_name):
    if hasattr(mod, "load_pipeline_as_needed"):
        monkeypatch.setattr(mod, "load_pipeline_as_needed", _fake_h3_loader_for(mod_name))


def _ensure_generate(worker):
    if not hasattr(worker, "generate") and hasattr(worker, "analyze"):
        worker.generate = worker.analyze
    return worker


# ---- 6 fixtures, each explicit ----


@pytest.fixture
def flash_cls(flash_platform, target, monkeypatch, request):
    mod_name = _infer(str(request.node.path))
    mod = importlib.import_module(mod_name)
    if "vision" in mod_name:
        _patch_vision(mod, monkeypatch)
    if "comfy" in mod_name:
        _patch_comfy(mod, monkeypatch)
    if "krea2" in mod_name:
        _patch_krea2_loader(mod, monkeypatch, mod_name)
    if "h3" in mod_name and "comfy" not in mod_name:
        _patch_h3_loader(mod, monkeypatch, mod_name)
    name, decorated = _decorated(mod, ("Endpoint",))
    cls = _flash_class(decorated)
    runner = flash_sync_runner_factory(target)
    spec = WorkerSpec(module=mod_name, attr=name, live_endpoint=_live_endpoint_for(mod_name), shape="flash_cls")

    def make(storage, _c=cls, _m=mod_name):
        try:
            pipe, _ = _fake_loader_for(_m)()
            inst = _c(storage, pipe=pipe)
        except TypeError:
            inst = _c(storage)
        return _ensure_generate(inst)

    return _Harness(flash_platform, runner, make, spec)


@pytest.fixture
def flash_pre(flash_platform, target, monkeypatch, request):
    mod_name = _infer(str(request.node.path))
    mod = importlib.import_module(mod_name)
    _patch_comfy(mod, monkeypatch)
    name, decorated = _decorated(mod, ("Endpoint",))
    cls = _flash_class(decorated)
    runner = flash_async_runner_factory(target)
    spec = WorkerSpec(module=mod_name, attr=name, live_endpoint=_live_endpoint_for(mod_name), shape="flash_pre")

    def make(storage, _c=cls):
        inst = _c(storage)
        return _ensure_generate(inst)

    return _Harness(flash_platform, runner, make, spec)


@pytest.fixture
def beam_eq(beam_platform, target, monkeypatch, request):
    mod_name = _infer(str(request.node.path))
    mod = importlib.import_module(mod_name)
    if "vision" in mod_name:
        _patch_vision(mod, monkeypatch)
    name, decorated = _decorated(mod, ("endpoint",))
    fn = _beam_unwrap(decorated)
    runner = beam_sync_runner_factory(target)
    loader = _fake_h3_loader_for(mod_name) if ("h3" in mod_name and "comfy" not in mod_name) else _fake_loader_for(mod_name)

    def make(storage, _f=fn, _l=loader, _m=mod_name):
        ctx = _FakeCtx(_fake_vision_ctx() if "vision" in _m else _l())
        w = types.SimpleNamespace()

        def _gen(**i):
            i.pop("storage", None)
            return _f(ctx, storage=storage, **i)

        w.generate = _gen
        return w

    spec = WorkerSpec(module=mod_name, attr=name, live_endpoint=_live_endpoint_for(mod_name), shape="beam_eq")
    return _Harness(beam_platform, runner, make, spec)


@pytest.fixture
def beam_tq(beam_platform, target, monkeypatch, request):
    mod_name = _infer(str(request.node.path))
    mod = importlib.import_module(mod_name)
    if "comfy" in mod_name:
        _patch_comfy(mod, monkeypatch)
    name, decorated = _decorated(mod, ("task_queue",))
    fn = _beam_unwrap(decorated)
    runner = beam_async_runner_factory(target)  # async flow
    is_comfy = "comfy" in mod_name
    if is_comfy:
        _patch_beam_comfy(mod, monkeypatch)
    if "krea2" in mod_name:
        loader = _fake_krea2_loader_for(mod_name)
    elif "h3" in mod_name and "comfy" not in mod_name:
        loader = _fake_h3_loader_for(mod_name)
    else:
        loader = _fake_loader_for(mod_name)

    def make(storage, _f=fn, _l=loader, _m=mod_name, _comfy=is_comfy):
        ctx = _FakeCtx("http://fake-comfy" if _comfy else (_fake_vision_ctx() if "vision" in _m else _l()))
        w = types.SimpleNamespace()

        def _gen(**i):
            i.pop("storage", None)
            return _f(ctx, storage=storage, **i)

        w.generate = _gen
        return w

    spec = WorkerSpec(module=mod_name, attr=name, live_endpoint=_live_endpoint_for(mod_name), shape="beam_tq")
    return _Harness(beam_platform, runner, make, spec)


@pytest.fixture
def beam_asgi(beam_platform, target, monkeypatch, request):
    mod_name = _infer(str(request.node.path))
    runner = beam_async_runner_factory(target)
    spec = WorkerSpec(module=mod_name, attr="worker", live_endpoint=_live_endpoint_for(mod_name), shape="beam_asgi")
    is_rest = "chatterbox" in mod_name

    def make(storage):
        class _W:
            def generate(self, **inputs):
                if inputs.get("type") == "failure" or any(
                    isinstance(v, str) and "failure" in v for v in inputs.values()
                ):
                    raise RuntimeError("inference failed: canned failure")
                if is_rest:
                    return {"audio": fake_mp4_stub(), "content_type": "audio/wav"}
                return {"type": "session.created", "session": inputs.get("session", {})}

        return _W()

    return _Harness(beam_platform, runner, make, spec)


@pytest.fixture
def modal_cls(modal_platform, target, monkeypatch, request):
    mod_name = _infer(str(request.node.path))
    mod = importlib.import_module(mod_name)
    if "vision" in mod_name:
        _patch_vision(mod, monkeypatch)
    if "krea2" in mod_name:
        _patch_krea2_loader(mod, monkeypatch, mod_name)
    if "h3" in mod_name and "comfy" not in mod_name:
        _patch_h3_loader(mod, monkeypatch, mod_name)
    name, decorated = _decorated(mod, ("cls",))
    cls = _modal_class(decorated)
    runner = modal_sync_runner_factory(target)
    spec = WorkerSpec(module=mod_name, attr=name, live_endpoint=_live_endpoint_for(mod_name), shape="modal_cls")

    # Voice chat worker has no generate/analyze: canned realtime event.
    if "voice_chat" in mod_name:
        def make_voice(storage):
            class _W:
                def generate(self, **inputs):
                    if any(isinstance(v, str) and "failure" in v for v in inputs.values()):
                        raise RuntimeError("inference failed: canned failure")
                    return {"type": "session.created", "session": inputs.get("session", {})}

            return _W()

        return _Harness(modal_platform, runner, make_voice, spec)

    def make(storage, _c=cls, _m=mod_name):
        inst = _c.__new__(_c)
        inst.storage = storage
        if "vision" in _m:
            inst.model, inst.processor, inst.analyze_prompt = (object(), object(), "fake")
        elif "h3" in _m and "comfy" not in _m:
            inst.pipe, inst.write_video_audio = _FakeH3Pipe(), _fake_write_video_audio
        elif "krea2" in _m:
            pipe, runtime_dir, torch_mod = _fake_krea2_loader_for(_m)()
            inst.pipe, inst.runtime_dir, inst.torch_module = pipe, runtime_dir, torch_mod
        else:
            vals = _fake_loader_for(_m)()
            vals = vals if isinstance(vals, tuple) else (vals,)
            for attr_name, val in zip(("pipe", "torch_module"), vals):
                try:
                    setattr(inst, attr_name, val)
                except Exception:
                    pass
        raw = getattr(_c, "generate", None) or getattr(_c, "analyze", None)
        raw = getattr(raw, "_get_raw_f", lambda: raw)()
        bound = raw.__get__(inst)
        inst.generate = lambda **i: bound(**{k: v for k, v in i.items() if k != "storage"})
        if hasattr(_c, "analyze"):
            inst.analyze = inst.generate
        return inst

    return _Harness(modal_platform, runner, make, spec)
