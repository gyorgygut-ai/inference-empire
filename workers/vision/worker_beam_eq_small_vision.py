from __future__ import annotations

from beam import Image, QueueDepthAutoscaler, Volume, endpoint

from workers.vision._shared_small_vision import (
    SmallVisionInput,
    SmallVisionOutput,
    do_inference,
    ensure_dotenv,
    load_dependencies,
)

ensure_dotenv()

CACHE_PATH = "./hf-cache"

image = (
    Image(python_version="python3.11")
    .add_python_packages(
        [
            "torch==2.9.1",
            "transformers>=5.0,<6",
            "torchvision==0.24.1",
            "pillow==12.3.0",
            "accelerate==1.14.0",
        ]
    )
    .with_envs(
        {
            "HF_HOME": CACHE_PATH,
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
        }
    )
)


def load_deps():
    return load_dependencies(cache_dir=CACHE_PATH)


def generate(model, processor, analyze_prompt, **kwargs) -> dict:
    """Validate at boundary, delegate, return output contract."""
    req = SmallVisionInput(**kwargs)
    try:
        result = do_inference(model, processor, analyze_prompt, req)
        return result.model_dump() if isinstance(result, SmallVisionOutput) else result
    except Exception as e:
        print(f"[ERR] {type(e).__name__}: {e}", flush=True)
        raise RuntimeError(f"inference failed: {e}") from e


@endpoint(
    name="small-vision-worker",
    cpu=2,
    memory="16Gi",
    gpu="A10G",
    image=image,
    on_start=load_deps,
    volumes=[Volume(name="hf-cache", mount_path=CACHE_PATH)],
    autoscaler=QueueDepthAutoscaler(max_containers=1, tasks_per_container=1),
    keep_warm_seconds=0,
    checkpoint_enabled=True,
)
def analyze(context, image_base64: str):
    model, processor, analyze_prompt = context.on_start_value
    return generate(model, processor, analyze_prompt, image_base64=image_base64)
