import os

from beam import Image, QueueDepthAutoscaler, Volume, asgi
from shared.worker_voice_llm_chat_completions import (
    MODELS,
    build_app,
)

image = (
    Image(python_version="python3.11")
    .add_python_packages(
        [
            "fastapi==0.141.1",
            "torch==2.6.0",
            "transformers==5.2.0",
            "accelerate==1.15.0",
            "huggingface-hub[hf-transfer]==1.29.0",
            "hf_xet==1.6.0",
            "bitsandbytes==0.50.2",
        ]
    )
    .with_envs(
        {
            "HF_HOME": "./hf-cache",
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "SECRET_HUGGINGFACE_TOKEN": os.environ["SECRET_HUGGINGFACE_TOKEN"],
        }
    )
)
model_volumes = [
    Volume(name=f"model-cache-{name}", mount_path=model["path"])
    for name, model in MODELS.items()
]


@asgi(
    name="workers-voice-llm-chat-completions",
    image=image,
    volumes=model_volumes,
    gpu="RTX4090",
    cpu=4,
    memory="32Gi",
    concurrent_requests=1,
    keep_warm_seconds=10,
    timeout=-1,
    authorized=True,
    secrets=[],
    autoscaler=QueueDepthAutoscaler(max_containers=1, min_containers=0),
)
def generate(context):
    del context
    return build_app()
