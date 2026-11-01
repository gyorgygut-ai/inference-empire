from __future__ import annotations

import os

from beam import Image, QueueDepthAutoscaler, task_queue
from dist.contract_krea2 import Input as Krea2Ref2ImgInput
from shared.platform import BEAM_CACHE_PATH, beam_env, beam_volume
from shared.worker_krea2 import DEPENDENCIES, do_inference, load_dependencies, load_pipeline_lazy

CACHE_PATH = BEAM_CACHE_PATH

image = Image(python_version="python3.11").add_python_packages(DEPENDENCIES).with_envs(
    beam_env(
        extra={
            "SECRET_HUGGINGFACE_TOKEN": os.environ["SECRET_HUGGINGFACE_TOKEN"],
            "SECRET_R2_ACCESS_KEY": os.environ["SECRET_R2_ACCESS_KEY"],
            "SECRET_R2_SECRET_KEY": os.environ["SECRET_R2_SECRET_KEY"],
            "SECRET_R2_ENDPOINT": os.environ["SECRET_R2_ENDPOINT"],
            "SECRET_R2_BUCKET": os.environ["SECRET_R2_BUCKET"],
            "PYTORCH_NVML_BASED_CUDA_CHECK": "0",
        }
    )
)

@task_queue(
    name="worker-krea2",
    cpu=8,
    memory="64Gi",
    gpu="RTX5090",
    image=image,
    on_start=lambda: load_dependencies(cache_dir=CACHE_PATH),
    volumes=[beam_volume(CACHE_PATH)],
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=0,
    checkpoint_enabled=True,
    timeout=300,
    secrets=[],
)
def generate(context, **kwargs) -> dict:
    storage, pipe, runtime_dir, torch_module = context.on_start_value
    if pipe is None:
        # Lazy load model on first request
        pipe, runtime_dir = load_pipeline_lazy(cache_dir=CACHE_PATH)
    req = Krea2Ref2ImgInput(**kwargs)
    return do_inference(pipe, runtime_dir, torch_module, storage, req).model_dump()
