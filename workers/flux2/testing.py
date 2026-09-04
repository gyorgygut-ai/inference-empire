"""Flux2 spec objects + fake builders."""

from workers.conftest import WorkerSpec
from workers.flux2.generate_flux2_klein9b import Flux2Klein9bInput


class FakePipe:
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


def fake_flux2_loader(*args, **kwargs):
    return FakePipe(), FakeTorch()


FLASH_ENDPOINT = "flux2-klein9b-worker"
MODAL_APP = "flux2-klein9b-worker"
BEAM_SLUG = "flux2-klein9b-worker"


FLUX2_FLASH_CLS = WorkerSpec(
    id="flux2-flash-cls",
    provider="flash",
    kind="sync",
    shape="flash_cls",
    module="workers.flux2.worker_flash_cls_flux2_klein9b",
    attr="FluxKleinWorker",
    method="generate",
    loader_attr="load_pipeline_as_needed",
    input_model=Flux2Klein9bInput,
    fake_builder=fake_flux2_loader,
    live_endpoint=FLASH_ENDPOINT,
)

FLUX2_BEAM_TQ = WorkerSpec(
    id="flux2-beam-tq",
    provider="beam",
    kind="async",
    shape="beam_tq",
    module="workers.flux2.worker_beam_tq_flux2_klein9b",
    attr="generate",
    input_model=Flux2Klein9bInput,
    fake_builder=fake_flux2_loader,
    live_endpoint=BEAM_SLUG,
)

FLUX2_MODAL_CLS = WorkerSpec(
    id="flux2-modal-cls",
    provider="modal",
    kind="sync",
    shape="modal_cls",
    module="workers.flux2.worker_modal_cls_flux2_klein9b",
    attr="FluxKleinWorker",
    method="generate",
    loader_attr="shared_load_pipeline",
    pipe_attrs=("pipe", "torch_module"),
    input_model=Flux2Klein9bInput,
    fake_builder=fake_flux2_loader,
    live_endpoint=MODAL_APP,
)
