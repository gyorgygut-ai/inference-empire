import os

from beam import Image, QueueDepthAutoscaler, Volume, asgi
from shared.worker_voice_stt_audio_transcriptions import build_app

image = (
    Image(python_version="python3.11")
    .add_python_packages(
        [
            "fastapi==0.141.1",
            "faster-whisper==1.2.1",
            "huggingface-hub[hf-transfer]==1.29.0",
            "hf_xet==1.6.0",
            "nvidia-cublas-cu12==12.8.4.1",
            "nvidia-cudnn-cu12==9.10.2.21",
            "python-multipart==0.0.32",
        ]
    )
    .with_envs(
        {
            "HF_HOME": "./hf-cache",
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "LD_LIBRARY_PATH": "/usr/local/lib/python3.11/dist-packages/nvidia/cublas/lib:/usr/local/lib/python3.11/dist-packages/nvidia/cudnn/lib",
            "SECRET_HUGGINGFACE_TOKEN": os.environ["SECRET_HUGGINGFACE_TOKEN"],
            "GENERATED_STT_AUDIO_TRANSCRIPTIONS_API_KEY": os.environ[
                "GENERATED_STT_AUDIO_TRANSCRIPTIONS_API_KEY"
            ],
        }
    )
)
model_volumes = [Volume(name="workers-voice-stt-hf-cache", mount_path="./hf-cache")]


@asgi(
    name="workers-voice-stt-audio-transcriptions",
    image=image,
    volumes=model_volumes,
    gpu="RTX4090",
    cpu=4,
    memory="16Gi",
    concurrent_requests=1,
    keep_warm_seconds=10,
    timeout=-1,
    authorized=False,
    secrets=[],
    autoscaler=QueueDepthAutoscaler(max_containers=1, min_containers=0),
)
def generate(context):
    del context
    return build_app()
