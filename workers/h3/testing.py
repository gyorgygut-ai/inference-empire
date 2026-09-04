"""H3 spec objects + fake builders."""

import base64

from workers.conftest import WorkerSpec, fake_mp4_stub
from workers.h3.generate_minimax_h3_comfy import MiniMaxH3ComfyInput
from workers.h3.generate_minimax_h3_fl2va import MiniMaxH3Fl2VAInput
from workers.h3.generate_minimax_h3_ref2va import MiniMaxH3Ref2VAInput
from workers.h3.generate_minimax_h3_ref2va_comfy import ValidatedRef2VAComfyInput


class FakePipe:
    def __init__(self):
        import numpy as np
        from types import SimpleNamespace

        self._video = np.zeros((1, 4, 64, 64, 3), dtype="uint8")
        self._audio = np.zeros((1, 24000), dtype="float32")
        self.audio_vae = SimpleNamespace(sample_rate=24000)

    def __call__(self, **kw):
        return self._video, self._audio


def fake_write_video_audio(*, video, audio, output_path, fps, audio_sample_rate):
    with open(output_path, "wb") as fh:
        fh.write(fake_mp4_stub())


def fake_h3_loader(*args, **kwargs):
    return FakePipe(), fake_write_video_audio


class FakeEndpoint:
    """Stand-in for runpod_flash Endpoint (comfy backend)."""

    async def runsync(self, payload, timeout=None):
        from types import SimpleNamespace

        return SimpleNamespace(
            error=None,
            output={"images": [{"data": base64.b64encode(fake_mp4_stub()).decode("ascii")}]},
        )


def fake_comfy_endpoint():
    return FakeEndpoint()


def fake_comfy_history():
    history = {
        "fake-prompt-id": {
            "outputs": {
                "save": {
                    "videos": [
                        {"filename": "fake.mp4", "subfolder": "", "type": "output"}
                    ]
                }
            }
        }
    }
    return history, fake_mp4_stub()


H3_FL2VA_ENDPOINT = "minimax-h3-fl2va-worker"
H3_REF2VA_ENDPOINT = "minimax-h3-ref2va-worker"
H3_COMFY_ENDPOINT = "minimax-h3-comfy-worker"
H3_REF2VA_COMFY_ENDPOINT = "minimax-h3-ref2va-comfy-worker"


H3_FL2VA_FLASH_CLS = WorkerSpec(
    id="h3-fl2va-flash-cls",
    provider="flash",
    kind="sync",
    shape="flash_cls",
    module="workers.h3.worker_flash_cls_minimax_h3_fl2va",
    attr="MiniMaxH3Fl2VAWorker",
    method="generate",
    loader_attr="load_pipeline_as_needed",
    input_model=MiniMaxH3Fl2VAInput,
    fake_builder=fake_h3_loader,
    live_endpoint=H3_FL2VA_ENDPOINT,
)

H3_FL2VA_BEAM_TQ = WorkerSpec(
    id="h3-fl2va-beam-tq",
    provider="beam",
    kind="async",
    shape="beam_tq",
    module="workers.h3.worker_beam_tq_minimax_h3_fl2va",
    attr="generate",
    input_model=MiniMaxH3Fl2VAInput,
    fake_builder=fake_h3_loader,
    live_endpoint=H3_FL2VA_ENDPOINT,
)

H3_FL2VA_MODAL_CLS = WorkerSpec(
    id="h3-fl2va-modal-cls",
    provider="modal",
    kind="sync",
    shape="modal_cls",
    module="workers.h3.worker_modal_cls_minimax_h3_fl2va",
    attr="MiniMaxH3Fl2VAWorker",
    method="generate",
    loader_attr="shared_load_pipeline",
    pipe_attrs=("pipe", "write_video_audio"),
    input_model=MiniMaxH3Fl2VAInput,
    fake_builder=fake_h3_loader,
    live_endpoint=H3_FL2VA_ENDPOINT,
)

H3_REF2VA_FLASH_CLS = WorkerSpec(
    id="h3-ref2va-flash-cls",
    provider="flash",
    kind="sync",
    shape="flash_cls",
    module="workers.h3.worker_flash_cls_minimax_h3_ref2va",
    attr="MiniMaxH3Ref2VAWorker",
    method="generate",
    loader_attr="load_pipeline_as_needed",
    input_model=MiniMaxH3Ref2VAInput,
    fake_builder=fake_h3_loader,
    live_endpoint=H3_REF2VA_ENDPOINT,
)

H3_REF2VA_BEAM_TQ = WorkerSpec(
    id="h3-ref2va-beam-tq",
    provider="beam",
    kind="async",
    shape="beam_tq",
    module="workers.h3.worker_beam_tq_minimax_h3_ref2va",
    attr="generate",
    input_model=MiniMaxH3Ref2VAInput,
    fake_builder=fake_h3_loader,
    live_endpoint=H3_REF2VA_ENDPOINT,
)

H3_REF2VA_MODAL_CLS = WorkerSpec(
    id="h3-ref2va-modal-cls",
    provider="modal",
    kind="sync",
    shape="modal_cls",
    module="workers.h3.worker_modal_cls_minimax_h3_ref2va",
    attr="MiniMaxH3Ref2VAWorker",
    method="generate",
    loader_attr="shared_load_pipeline",
    pipe_attrs=("pipe", "write_video_audio"),
    input_model=MiniMaxH3Ref2VAInput,
    fake_builder=fake_h3_loader,
    live_endpoint=H3_REF2VA_ENDPOINT,
)

H3_COMFY_FLASH_CLS = WorkerSpec(
    id="h3-comfy-flash-cls",
    provider="flash",
    kind="sync",
    shape="flash_comfy",
    module="workers.h3.worker_flash_cls_minimax_h3_comfy",
    attr="MiniMaxH3ComfyWorker",
    method="generate",
    input_model=MiniMaxH3ComfyInput,
    fake_builder=fake_comfy_endpoint,
    live_endpoint=H3_COMFY_ENDPOINT,
)

H3_REF2VA_COMFY_FLASH_PRE = WorkerSpec(
    id="h3-ref2va-comfy-flash-pre",
    provider="flash",
    kind="sync",
    shape="flash_comfy",
    module="workers.h3.worker_flash_pre_minimax_h3_ref2va_comfy",
    attr="MiniMaxH3Ref2VAComfyWorker",
    method="generate",
    input_model=ValidatedRef2VAComfyInput,
    fake_builder=fake_comfy_endpoint,
    live_endpoint=H3_REF2VA_COMFY_ENDPOINT,
)

H3_REF2VA_COMFY_BEAM_TQ = WorkerSpec(
    id="h3-ref2va-comfy-beam-tq",
    provider="beam",
    kind="async",
    shape="beam_comfy",
    module="workers.h3.worker_beam_tq_minimax_h3_ref2va_comfy",
    attr="generate",
    input_model=ValidatedRef2VAComfyInput,
    fake_builder=fake_comfy_history,
    live_endpoint=H3_REF2VA_COMFY_ENDPOINT,
)
