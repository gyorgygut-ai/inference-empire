import os

from beam import Image, QueueDepthAutoscaler, asgi
from shared.worker_voice import build_app

image = (
    Image(python_version="python3.11")
    .add_python_packages(
        [
            "aiortc==1.15.0",
            "av==17.1.0",
            "fastapi==0.141.1",
            "fastrtc[vad] @ git+https://github.com/gradio-app/fastrtc@59ca4f77e1669a9599c0895fd0d7c39f356bf89f",
            "httpx==0.28.1",
            "numpy==2.4.3",
            "python-multipart==0.0.32",
            "soundfile==0.14.0",
        ]
    )
    .with_envs(
        {
            "SECRET_HUGGINGFACE_TOKEN": os.environ["SECRET_HUGGINGFACE_TOKEN"],
            "STT_AUDIO_TRANSCRIPTIONS_API_URL": os.environ[
                "STT_AUDIO_TRANSCRIPTIONS_API_URL"
            ],
            "SECRET_STT_AUDIO_TRANSCRIPTIONS_API_KEY": os.environ[
                "SECRET_STT_AUDIO_TRANSCRIPTIONS_API_KEY"
            ],
            "LLM_CHAT_COMPLETIONS_API_URL": os.environ[
                "LLM_CHAT_COMPLETIONS_API_URL"
            ],
            "SECRET_LLM_CHAT_COMPLETIONS_API_KEY": os.environ[
                "SECRET_LLM_CHAT_COMPLETIONS_API_KEY"
            ],
            "TTS_AUDIO_SPEECH_API_URL": os.environ[
                "TTS_AUDIO_SPEECH_API_URL"
            ],
            "SECRET_VOICE_WORKER_AUTH_TOKEN": os.environ[
                "SECRET_VOICE_WORKER_AUTH_TOKEN"
            ],
            "SECRET_TTS_AUDIO_SPEECH_API_KEY": os.environ[
                "SECRET_TTS_AUDIO_SPEECH_API_KEY"
            ],
        }
    )
)


@asgi(
    name="worker-voice",
    image=image,
    cpu=2,
    memory="4Gi",
    keep_warm_seconds=10,
    timeout=120,
    authorized=False,
    secrets=[],
    autoscaler=QueueDepthAutoscaler(max_containers=1, min_containers=0),
)
def generate(context):
    del context
    return build_app()
