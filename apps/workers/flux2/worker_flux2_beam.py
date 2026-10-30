from __future__ import annotations

from beam import Image, QueueDepthAutoscaler, task_queue
from dist.contract_flux2 import Input as Flux2Klein9bInput
from shared.platform import beam_env
from shared.worker_flux2 import (
    DEPENDENCIES,
    MODEL_CACHES,
    do_inference,
    load_dependencies,
    model_volumes,
)

CACHE_PATH = MODEL_CACHES["flux2_klein9b_sdnq4"]["path"]
VOLUMES = model_volumes()

image = Image(python_version="python3.11").add_python_packages(DEPENDENCIES).with_envs(
    beam_env(cache_path=CACHE_PATH, extra={"SDNQ_USE_TRITON_MM": "0"})
)

@task_queue(
    name="workers-flux2",
    cpu=4,
    memory="32Gi",
    gpu="RTX4090",
    image=image,
    on_start=load_dependencies,
    volumes=VOLUMES,
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=0,
    checkpoint_enabled=True,
    timeout=300,
    secrets=["HF_TOKEN", "R2_ACCESS_KEY", "R2_SECRET_KEY", "R2_ENDPOINT"],
)
def generate(context, **kwargs) -> dict:
    storage, pipe, torch_module = context.on_start_value
    req = Flux2Klein9bInput(**kwargs)
    return do_inference(pipe, torch_module, storage, req).model_dump()
