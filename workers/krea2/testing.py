"""Krea2 spec objects + fake builders."""

import tempfile

from workers.conftest import WorkerSpec
from workers.krea2.generate_krea2_ref2img import Krea2Ref2ImgInput


class FakePipe:
    def set_adapters(self, *args, **kwargs):
        pass

    def __call__(self, **kw):
        from workers.conftest import fake_png

        from PIL import Image
        import io

        out = type("Out", (), {})()
        out.images = [Image.open(io.BytesIO(fake_png()))]
        return out


class FakeTorch:
    class Generator:
        def __init__(self, device=None):
            pass

        def manual_seed(self, seed):
            return self


def fake_krea2_loader(*args, **kwargs):
    # Empty models/ dir: face_crop's onnx glob misses and returns img as-is.
    return FakePipe(), tempfile.mkdtemp(prefix="krea2_fake_"), FakeTorch()


FLASH_ENDPOINT = "krea2-ref2img-worker"
MODAL_APP = "krea2-ref2img-worker"
BEAM_SLUG = "krea2-ref2img-worker"


KREA2_FLASH_CLS = WorkerSpec(
    id="krea2-flash-cls",
    provider="flash",
    kind="sync",
    shape="flash_cls",
    module="workers.krea2.worker_flash_cls_krea2_ref2img",
    attr="Krea2Ref2ImgWorker",
    method="generate",
    loader_attr="load_pipeline_as_needed",
    input_model=Krea2Ref2ImgInput,
    fake_builder=fake_krea2_loader,
    live_endpoint=FLASH_ENDPOINT,
)

KREA2_BEAM_TQ = WorkerSpec(
    id="krea2-beam-tq",
    provider="beam",
    kind="async",
    shape="beam_tq",
    module="workers.krea2.worker_beam_tq_krea2_ref2img",
    attr="generate",
    input_model=Krea2Ref2ImgInput,
    fake_builder=fake_krea2_loader,
    live_endpoint=BEAM_SLUG,
)

KREA2_MODAL_CLS = WorkerSpec(
    id="krea2-modal-cls",
    provider="modal",
    kind="sync",
    shape="modal_cls",
    module="workers.krea2.worker_modal_cls_krea2_ref2img",
    attr="Krea2Ref2ImgWorker",
    method="generate",
    loader_attr="shared_load_pipeline",
    pipe_attrs=("pipe", "runtime_dir", "torch_module"),
    input_model=Krea2Ref2ImgInput,
    fake_builder=fake_krea2_loader,
    live_endpoint=MODAL_APP,
)
