"""Vision spec objects + fake builders.

Fake = canned output, no image handling. The sentinel `"failure"` raises;
anything else returns the contract.
"""

from workers.conftest import WorkerSpec
from workers.vision.analyze_small_vision import SmallVisionInput, SmallVisionOutput

CANNED = {"classification": "landscape_0p", "subjects": ["hill"], "description": "canned"}


def fake_vision_loader(*args, **kwargs):
    return object(), object(), "prompt"


def fake_run_analyze(model, processor, analyze_prompt, req):
    if getattr(req, "image_base64", "") == "failure":
        raise RuntimeError("inference failed: canned failure")
    return SmallVisionOutput(**CANNED)


FLASH_ENDPOINT = "small-vision-worker"
MODAL_APP = "small-vision-worker"
BEAM_SLUG = "small-vision-worker"
# Serving shapes resolve to URLs only after deploy; the owner pastes the
# deployed URL (identity slugs cannot address serving endpoints).
VISION_BEAM_URL = "owner: paste deployed https URL for small-vision-worker endpoint"


VISION_FLASH_CLS = WorkerSpec(
    id="vision-flash-cls",
    provider="flash",
    kind="sync",
    shape="flash_cls",
    module="workers.vision.worker_flash_cls_small_vision",
    attr="Qwen2VLVisionWorker",
    method="analyze",
    loader_attr="load_models_as_needed",
    input_model=SmallVisionInput,
    fake_builder=fake_vision_loader,
    run_fake_name="run_analyze",
    run_fake=fake_run_analyze,
    live_endpoint=FLASH_ENDPOINT,
)

VISION_BEAM_EQ = WorkerSpec(
    id="vision-beam-eq",
    provider="beam",
    kind="sync",
    shape="beam_eq",
    module="workers.vision.worker_beam_eq_small_vision",
    attr="analyze",
    input_model=SmallVisionInput,
    fake_builder=fake_vision_loader,
    run_fake_name="run_analyze",
    run_fake=fake_run_analyze,
    live_endpoint=VISION_BEAM_URL,
)

VISION_MODAL_CLS = WorkerSpec(
    id="vision-modal-cls",
    provider="modal",
    kind="sync",
    shape="modal_cls",
    module="workers.vision.worker_modal_cls_small_vision",
    attr="SmallVisionWorker",
    method="analyze",
    loader_attr="shared_load_models",
    pipe_attrs=("model", "processor", "analyze_prompt"),
    input_model=SmallVisionInput,
    fake_builder=fake_vision_loader,
    run_fake_name="run_analyze",
    run_fake=fake_run_analyze,
    live_endpoint=MODAL_APP,
)
