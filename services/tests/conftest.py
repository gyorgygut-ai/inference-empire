import sys
import types

import pytest


def _install_modal_mock():
    if "modal" in sys.modules:
        return
    _m = types.ModuleType("modal")

    class _FakeVolume:
        @staticmethod
        def from_name(*a, **kw):
            return _FakeVolume()

        def commit(self):
            pass

        def reload(self):
            pass

    class _FakeImage:
        @staticmethod
        def debian_slim(*a, **kw):
            return _FakeImage()

        def run_commands(self, *a, **kw):
            return self

        def pip_install(self, *a, **kw):
            return self

        def apt_install(self, *a, **kw):
            return self

        def env(self, *a, **kw):
            return self

        def run_function(self, *a, **kw):
            return self

    class _FakeSecret:
        @staticmethod
        def from_dotenv(*a, **kw):
            return _FakeSecret()

        @staticmethod
        def from_dict(*a, **kw):
            return _FakeSecret()

    class _FakeApp:
        def __init__(self, *a, **kw):
            pass

        def cls(self, *a, **kw):
            return lambda cls: cls

        def local_entrypoint(self, *a, **kw):
            def dec(f):
                return f

            return dec

    class _FakeCls:
        @staticmethod
        def from_name(*a, **kw):
            return _FakeCls()

        def remote(self, *a, **kw):
            return {}

        def local(self, *a, **kw):
            return self

    class _FakeFunction:
        @staticmethod
        def from_name(*a, **kw):
            return _FakeFunction()

        def remote(self, *a, **kw):
            return {}

    def _d(*a, **kw):
        def dec(f):
            return f

        return dec

    _m.Volume = _FakeVolume
    _m.Image = _FakeImage
    _m.Secret = _FakeSecret
    _m.App = _FakeApp
    _m.Cls = _FakeCls
    _m.Function = _FakeFunction
    _m.method = _d
    _m.enter = _d
    _m.fastapi_endpoint = _d
    sys.modules["modal"] = _m


def _install_beam_mock():
    if "beam" in sys.modules:
        return
    beam_mock = types.ModuleType("beam")

    class _FakeBeamImage:
        def __init__(self, **kw):
            pass

        def add_python_packages(self, pkgs):
            return self

        def with_envs(self, envs):
            return self

        def add_commands(self, cmds):
            return self

        @staticmethod
        def from_registry(*a, **kw):
            return _FakeBeamImage()

    beam_mock.Image = _FakeBeamImage
    beam_mock.QueueDepthAutoscaler = type(
        "QueueDepthAutoscaler", (), {"__init__": lambda s, **kw: None}
    )
    beam_mock.Volume = type("Volume", (), {"__init__": lambda s, **kw: None})
    beam_mock.task_queue = lambda **kw: lambda f: f
    beam_mock.endpoint = lambda **kw: lambda f: f
    sys.modules["beam"] = beam_mock


def _install_runpod_flash_mock():
    if "runpod_flash" in sys.modules:
        return
    flash_mock = types.ModuleType("runpod_flash")

    class FakeGpuGroup:
        AMPERE_16 = "AMPERE_16"
        AMPERE_48 = "AMPERE_48"
        ADA_48_PRO = "ADA_48_PRO"

    def FakeEndpoint(**kw):
        def dec(cls):
            cls.__wrapped__ = cls
            return cls

        return dec

    flash_mock.Endpoint = FakeEndpoint
    flash_mock.GpuGroup = FakeGpuGroup
    sys.modules["runpod_flash"] = flash_mock


_install_modal_mock()
_install_beam_mock()
_install_runpod_flash_mock()


def pytest_addoption(parser):
    parser.addoption("--target", default="fake", help="'fake' or 'live")


class BeamWorkerProxy:
    def __init__(self, generate_fn, storage=None):
        self._generate = generate_fn
        self.storage = storage

    def generate(self, **inputs):
        class _FakeContext:
            on_start_value = (None, None, None)

        return self._generate(_FakeContext(), storage=self.storage, **inputs)


class VisionFlashWorkerProxy:
    def __init__(self, worker):
        self._worker = worker

    def generate(self, **inputs):
        return self._worker.analyze(**inputs)


class VisionBeamWorkerProxy:
    def __init__(self, analyze_fn, storage=None):
        self._analyze = analyze_fn
        self.storage = storage

    def generate(self, **inputs):
        class _FakeContext:
            on_start_value = (None, None, None)

        return self._analyze(_FakeContext(), storage=self.storage, **inputs)


class VisionModalWorkerProxy:
    def __init__(self, worker):
        self._worker = worker

    def generate(self, **inputs):
        return self._worker.analyze(**inputs)


def _make_vision_flash(storage):
    from vision.worker_flash_cls_small_vision import Qwen2VLVisionWorker

    class _FakePipe:
        pass

    return VisionFlashWorkerProxy(Qwen2VLVisionWorker(pipe=_FakePipe(), storage=storage))


def _make_vision_beam(storage):
    from vision.worker_beam_eq_small_vision import analyze

    return VisionBeamWorkerProxy(analyze, storage=storage)


def _make_vision_modal(storage):
    from vision.worker_modal_cls_small_vision import SmallVisionWorker

    return VisionModalWorkerProxy(SmallVisionWorker(storage=storage))


def _make_flux2_flash(storage):
    from flux2.worker_flash_cls_flux2_klein9b import FluxKleinWorker

    class _FakePipe:
        def set_adapters(self, *a, **kw):
            pass

    return FluxKleinWorker(pipe=_FakePipe(), storage=storage)


def _make_flux2_beam(storage):
    from flux2.worker_beam_tq_flux2_klein9b import generate

    return BeamWorkerProxy(generate, storage=storage)


def _make_flux2_modal(storage):
    from flux2.worker_modal_cls_flux2_klein9b import FluxKleinWorker

    class _FakePipe:
        def set_adapters(self, *a, **kw):
            pass

    return FluxKleinWorker(pipe=_FakePipe(), storage=storage)


def _make_krea2_flash(storage):
    from krea2.worker_flash_cls_krea2_ref2img import Krea2Ref2ImgWorker

    class _FakePipe:
        def set_adapters(self, *a, **kw):
            pass

    return Krea2Ref2ImgWorker(pipe=_FakePipe(), storage=storage)


def _make_krea2_beam(storage):
    from krea2.worker_beam_tq_krea2_ref2img import generate

    return BeamWorkerProxy(generate, storage=storage)


def _make_krea2_modal(storage):
    from krea2.worker_modal_cls_krea2_ref2img import Krea2Ref2ImgWorker

    class _FakePipe:
        def set_adapters(self, *a, **kw):
            pass

    return Krea2Ref2ImgWorker(pipe=_FakePipe(), storage=storage)


def _make_h3_flash(storage, variant="ref2va"):
    if variant == "fl2va":
        from h3.worker_flash_cls_minimax_h3_fl2va import MiniMaxH3Fl2VAWorker

        class _FakePipe:
            pass

        return MiniMaxH3Fl2VAWorker(pipe=_FakePipe(), storage=storage)
    elif variant == "comfy_pre":
        from h3.worker_flash_pre_minimax_h3_ref2va_comfy import MiniMaxH3Ref2VAComfyWorker

        class _FakePipe:
            pass

        return MiniMaxH3Ref2VAComfyWorker(pipe=_FakePipe(), storage=storage)
    elif variant == "comfy":
        from h3.worker_flash_cls_minimax_h3_comfy import MiniMaxH3ComfyWorker

        class _FakePipe:
            pass

        return MiniMaxH3ComfyWorker(pipe=_FakePipe(), storage=storage)
    else:
        from h3.worker_flash_cls_minimax_h3_ref2va import MiniMaxH3Ref2VAWorker

        class _FakePipe:
            pass

        return MiniMaxH3Ref2VAWorker(pipe=_FakePipe(), storage=storage)


def _make_h3_beam(storage, variant="ref2va"):
    if variant == "fl2va":
        from h3.worker_beam_tq_minimax_h3_fl2va import generate
    elif variant == "comfy":
        from h3.worker_beam_tq_minimax_h3_ref2va_comfy import generate
    else:
        from h3.worker_beam_tq_minimax_h3_ref2va import generate

    return BeamWorkerProxy(generate, storage=storage)


def _make_h3_modal(storage, variant="ref2va"):
    if variant == "fl2va":
        from h3.worker_modal_cls_minimax_h3_fl2va import MiniMaxH3Fl2VAWorker

        class _FakePipe:
            pass

        return MiniMaxH3Fl2VAWorker(pipe=_FakePipe(), storage=storage)
    else:
        from h3.worker_modal_cls_minimax_h3_ref2va import MiniMaxH3Ref2VAWorker

        class _FakePipe:
            pass

        return MiniMaxH3Ref2VAWorker(pipe=_FakePipe(), storage=storage)


def _detect_service(test_path):
    for svc in ["vision", "flux2", "krea2", "h3"]:
        if f"/{svc}/" in test_path:
            return svc
    return None


def _detect_h3_variant(test_file):
    if "fl2va" in test_file:
        return "fl2va"
    elif "comfy_pre" in test_file or ("comfy" in test_file and "pre" in test_file):
        return "comfy_pre"
    elif "comfy" in test_file:
        return "comfy"
    return "ref2va"


def _get_worker_factory(service, test_file, target):
    is_beam = "beam" in test_file
    is_modal = "modal" in test_file

    if service == "vision":
        if is_beam:
            return _make_vision_beam
        elif is_modal:
            return _make_vision_modal
        else:
            return _make_vision_flash
    elif service == "flux2":
        if is_beam:
            return _make_flux2_beam
        elif is_modal:
            return _make_flux2_modal
        else:
            return _make_flux2_flash
    elif service == "krea2":
        if is_beam:
            return _make_krea2_beam
        elif is_modal:
            return _make_krea2_modal
        else:
            return _make_krea2_flash
    elif service == "h3":
        variant = _detect_h3_variant(test_file)
        if is_beam:
            return lambda storage: _make_h3_beam(storage, variant)
        elif is_modal:
            return lambda storage: _make_h3_modal(storage, variant)
        else:
            return lambda storage: _make_h3_flash(storage, variant)
    return None


@pytest.fixture(scope="module")
def storage(request):
    if request.config.getoption("--target") == "live":
        from services.real_r2 import RealR2Storage

        return RealR2Storage()
    from services.fake_r2 import FakeR2Storage

    return FakeR2Storage()


@pytest.fixture(scope="module")
def platform(request):
    target = request.config.getoption("--target")
    test_file = request.fspath.basename
    test_path = str(request.fspath)
    service = _detect_service(test_path)
    factory = _get_worker_factory(service, test_file, target)

    if "beam" in test_file:
        if target == "live":
            from services.beam_platform import RealBeamPlatform

            return RealBeamPlatform(worker_factory=factory)
        from services.beam_platform_fake import FakeBeamPlatform

        return FakeBeamPlatform(worker_factory=factory)
    elif "modal" in test_file:
        if target == "live":
            from services.modal_platform import RealModalPlatform

            return RealModalPlatform(worker_factory=factory)
        from services.modal_platform_fake import FakeModalPlatform

        return FakeModalPlatform(worker_factory=factory)
    else:
        if target == "live":
            from services.flash_platform import RealFlashPlatform

            return RealFlashPlatform(worker_factory=factory)
        from services.flash_platform_fake import FakeFlashPlatform

        return FakeFlashPlatform(worker_factory=factory)


@pytest.fixture(scope="module")
def runner(request):
    test_file = request.fspath.basename
    if "flash" in test_file:
        from services.flash_runner import DirectSyncRunner

        return DirectSyncRunner()
    elif "beam" in test_file:
        from services.beam_runner import DirectAsyncRunner

        return DirectAsyncRunner()
    elif "modal" in test_file:
        from services.modal_runner import DirectAsyncRunner

        return DirectAsyncRunner()


@pytest.fixture(scope="module", autouse=True)
def lifecycle(platform):
    platform.deploy()
    yield
    platform.undeploy()
