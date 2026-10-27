from __future__ import annotations

from beam import Image, QueueDepthAutoscaler, task_queue
from shared.contract_tiny_sd import TinySDInput
from shared.platform import BEAM_CACHE_PATH, beam_env, beam_volume
from shared.worker_tiny_sd import DEPENDENCIES, do_inference, load_dependencies

CACHE_PATH = BEAM_CACHE_PATH

image = Image(python_version="python3.11").add_python_packages(DEPENDENCIES).with_envs(beam_env())

@task_queue(
    name="workers-tiny_sd",
    cpu=4,
    memory="32Gi",
    gpu="RTX4090",
    image=image,
    on_start=load_dependencies,
    volumes=[beam_volume(CACHE_PATH)],
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=0,
    checkpoint_enabled=True,
    timeout=300,
    secrets=["HF_TOKEN", "R2_ACCESS_KEY", "R2_SECRET_KEY", "R2_ENDPOINT"],
)
def generate(context, **kwargs) -> dict:
    storage, pipe, torch_module = context.on_start_value
    req = TinySDInput(**kwargs)
    return do_inference(pipe, torch_module, storage, req).model_dump()
