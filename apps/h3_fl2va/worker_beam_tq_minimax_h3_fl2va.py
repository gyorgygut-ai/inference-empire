from __future__ import annotations

from functools import partial

from beam import Image, QueueDepthAutoscaler, task_queue

from apps.h3_fl2va.shared.worker_h3_fl2va import (
    MiniMaxH3TurboFl2vaInput,
    do_inference,
    load_dependencies,
)
from packages.artifacts.r2_artifacts import R2Artifacts
from packages.shared_gpu.guard import run_guarded
from packages.shared_gpu.platform import BEAM_CACHE_PATH, beam_env, beam_volume

CACHE_PATH = BEAM_CACHE_PATH

image = (
    Image(python_version="python3.11")
    .add_python_packages([
        "torch==2.9.1",
        "torchcodec==0.9.0",
        "diffsynth[audio]==2.1.6",
        "diffusers==0.40.0",
            "transformers==5.16.1",
        "accelerate==1.14.0",
        "bitsandbytes==0.50.2",
            "pillow==12.3.0",
        "imageio==2.37.2",
        "imageio-ffmpeg==0.6.0",
            "torchaudio==2.9.1",
        "boto3==1.43.83",
    ])
    .with_envs({
        **beam_env(),
        "DIFFSYNTH_DOWNLOAD_SOURCE": "huggingface",
        "DIFFSYNTH_MODEL_BASE_PATH": f"{CACHE_PATH}/diffsynth",
    })
)


def load_deps():
    return load_dependencies(cache_dir=CACHE_PATH)


def generate(storage, pipe, write_video_audio, **kwargs) -> dict:
    return run_guarded(
        MiniMaxH3TurboFl2vaInput,
        kwargs,
        partial(do_inference, pipe, write_video_audio, storage),
    )


@task_queue(
    name="minimax-h3-fl2va-worker",
    cpu=1,
    memory="32Gi",
    gpu="RTX4090",
    image=image,
    on_start=load_deps,
    volumes=[beam_volume(CACHE_PATH)],
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=1800,
    checkpoint_enabled=True,
    timeout=3600,
    secrets=["HF_TOKEN", "R2_ACCESS_KEY", "R2_SECRET_KEY", "R2_ENDPOINT"],
    env={
        "R2_BUCKET": "generated-media",
        "R2_ENDPOINT": "https://29b2f092b2dbc0b63f48f491ddc177ee.r2.cloudflarestorage.com",
    },
)
def dispatch(context, **kwargs) -> dict:
    storage, pipe, write_video_audio = context.on_start_value
    return generate(storage, pipe, write_video_audio, **kwargs)
