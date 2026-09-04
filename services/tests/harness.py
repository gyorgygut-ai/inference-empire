import pytest


def pytest_addoption(parser):
    parser.addoption("--target", default="fake", help="'fake' or 'live")


class BeamWorkerProxy:
    def __init__(self, generate_fn, storage=None):
        self._generate = generate_fn
        self.storage = storage

    def generate(self, **inputs):
        return self._generate(storage=self.storage, **inputs)


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
        return self._analyze(storage=self.storage, **inputs)


class VisionModalWorkerProxy:
    def __init__(self, worker):
        self._worker = worker

    def generate(self, **inputs):
        return self._worker.analyze(**inputs)


def make_vision_flash_worker(storage=None):
    from vision.worker_flash_cls_small_vision import Qwen2VLVisionWorker

    class _FakePipe:
        pass

    if storage is None:
        return VisionFlashWorkerProxy(Qwen2VLVisionWorker())
    return VisionFlashWorkerProxy(Qwen2VLVisionWorker(pipe=_FakePipe(), storage=storage))


def make_vision_beam_worker(storage=None):
    from vision.worker_beam_eq_small_vision import analyze

    return VisionBeamWorkerProxy(analyze, storage=storage)


def make_vision_modal_worker(storage=None):
    from vision.worker_modal_cls_small_vision import SmallVisionWorker

    return VisionModalWorkerProxy(SmallVisionWorker())


def make_flux2_flash_worker(storage=None):
    from flux2.worker_flash_cls_flux2_klein9b import FluxKleinWorker

    class _FakePipe:
        def set_adapters(self, *a, **kw):
            pass

    if storage is None:
        return FluxKleinWorker()
    return FluxKleinWorker(pipe=_FakePipe(), storage=storage)


def make_flux2_beam_worker(storage=None):
    from flux2.worker_beam_tq_flux2_klein9b import generate

    return BeamWorkerProxy(generate, storage=storage)


def make_flux2_modal_worker(storage=None):
    from flux2.worker_modal_cls_flux2_klein9b import FluxKleinWorker

    class _FakePipe:
        def set_adapters(self, *a, **kw):
            pass

    if storage is None:
        return FluxKleinWorker()
    return FluxKleinWorker(pipe=_FakePipe(), storage=storage)


def make_krea2_flash_worker(storage=None):
    from krea2.worker_flash_cls_krea2_ref2img import Krea2Ref2ImgWorker

    class _FakePipe:
        def set_adapters(self, *a, **kw):
            pass

    if storage is None:
        return Krea2Ref2ImgWorker()
    return Krea2Ref2ImgWorker(pipe=_FakePipe(), storage=storage)


def make_krea2_beam_worker(storage=None):
    from krea2.worker_beam_tq_krea2_ref2img import generate

    return BeamWorkerProxy(generate, storage=storage)


def make_krea2_modal_worker(storage=None):
    from krea2.worker_modal_cls_krea2_ref2img import Krea2Ref2ImgWorker

    class _FakePipe:
        def set_adapters(self, *a, **kw):
            pass

    if storage is None:
        return Krea2Ref2ImgWorker()
    return Krea2Ref2ImgWorker(pipe=_FakePipe(), storage=storage)


def make_h3_flash_worker(storage=None, variant="ref2va"):
    if variant == "fl2va":
        from h3.worker_flash_cls_minimax_h3_fl2va import MiniMaxH3Fl2VAWorker

        class _FakePipe:
            pass

        if storage is None:
            return MiniMaxH3Fl2VAWorker()
        return MiniMaxH3Fl2VAWorker(pipe=_FakePipe(), storage=storage)
    elif variant == "comfy_pre":
        from h3.worker_flash_pre_minimax_h3_ref2va_comfy import MiniMaxH3Ref2VAComfyWorker

        class _FakePipe:
            pass

        if storage is None:
            return MiniMaxH3Ref2VAComfyWorker()
        return MiniMaxH3Ref2VAComfyWorker(pipe=_FakePipe(), storage=storage)
    elif variant == "comfy":
        from h3.worker_flash_cls_minimax_h3_comfy import MiniMaxH3ComfyWorker

        class _FakePipe:
            pass

        if storage is None:
            return MiniMaxH3ComfyWorker()
        return MiniMaxH3ComfyWorker(pipe=_FakePipe(), storage=storage)
    else:
        from h3.worker_flash_cls_minimax_h3_ref2va import MiniMaxH3Ref2VAWorker

        class _FakePipe:
            pass

        if storage is None:
            return MiniMaxH3Ref2VAWorker()
        return MiniMaxH3Ref2VAWorker(pipe=_FakePipe(), storage=storage)


def make_h3_beam_worker(storage=None, variant="ref2va"):
    if variant == "fl2va":
        from h3.worker_beam_tq_minimax_h3_fl2va import generate
    elif variant == "comfy":
        from h3.worker_beam_tq_minimax_h3_ref2va_comfy import generate
    else:
        from h3.worker_beam_tq_minimax_h3_ref2va import generate

    return BeamWorkerProxy(generate, storage=storage)


def make_h3_modal_worker(storage=None, variant="ref2va"):
    if variant == "fl2va":
        from h3.worker_modal_cls_minimax_h3_fl2va import MiniMaxH3Fl2VAWorker

        class _FakePipe:
            pass

        if storage is None:
            return MiniMaxH3Fl2VAWorker()
        return MiniMaxH3Fl2VAWorker(pipe=_FakePipe(), storage=storage)
    else:
        from h3.worker_modal_cls_minimax_h3_ref2va import MiniMaxH3Ref2VAWorker

        class _FakePipe:
            pass

        if storage is None:
            return MiniMaxH3Ref2VAWorker()
        return MiniMaxH3Ref2VAWorker(pipe=_FakePipe(), storage=storage)


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

    if "beam" in test_file:
        if target == "live":
            from services.beam_platform import RealBeamPlatform

            return RealBeamPlatform()
        from services.beam_platform_fake import FakeBeamPlatform

        return FakeBeamPlatform()
    elif "modal" in test_file:
        if target == "live":
            from services.modal_platform import RealModalPlatform

            return RealModalPlatform()
        from services.modal_platform_fake import FakeModalPlatform

        return FakeModalPlatform()
    else:
        if target == "live":
            from services.flash_platform import RealFlashPlatform

            return RealFlashPlatform()
        from services.flash_platform_fake import FakeFlashPlatform

        return FakeFlashPlatform()


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
