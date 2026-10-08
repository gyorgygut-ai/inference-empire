from __future__ import annotations

from functools import partial

from beam import Image, QueueDepthAutoscaler, task_queue

from packages.krea2.shared import (
    IMAGE_PIP_DEPS,
    Krea2Ref2ImgInput,
    do_inference,
    load_dependencies,
)
from packages.shared_gpu.guard import run_guarded
from packages.shared_gpu.platform import BEAM_CACHE_PATH, beam_env, beam_volume

CACHE_PATH = BEAM_CACHE_PATH

image = (
    Image(python_version="python3.11")
    .add_python_packages(list(IMAGE_PIP_DEPS))
    .with_envs(beam_env())
)


def load_deps():
    return load_dependencies(cache_dir=CACHE_PATH)


def generate(storage, pipe, runtime_dir, torch_module, **kwargs) -> dict:
    return run_guarded(
        Krea2Ref2ImgInput,
        kwargs,
        partial(do_inference, pipe, runtime_dir, torch_module, storage),
    )


@task_queue(
    name="krea2-ref2img-worker",
    cpu=8,
    memory="64Gi",
    gpu="RTX5090",
    image=image,
    on_start=load_deps,
    volumes=[beam_volume(CACHE_PATH)],
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=1800,
    checkpoint_enabled=True,
    timeout=300,
    secrets=["HF_TOKEN", "R2_ACCESS_KEY", "R2_SECRET_KEY", "R2_ENDPOINT"],
    env={
        "PYTORCH_NVML_BASED_CUDA_CHECK": "0",
    },
)
def dispatch(context, **kwargs) -> dict:
    storage, pipe, runtime_dir, torch_module = context.on_start_value
    return generate(storage, pipe, runtime_dir, torch_module, **kwargs)
