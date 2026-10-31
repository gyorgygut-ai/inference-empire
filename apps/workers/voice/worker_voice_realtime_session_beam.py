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
            "fastrtc[vad]==0.0.34",
            "httpx==0.28.1",
            "numpy==2.4.3",
            "python-multipart==0.0.32",
            "soundfile==0.14.0",
        ]
    )
    .with_envs(
        {
            "STT_AUDIO_TRANSCRIPTIONS_API_URL": os.environ[
                "STT_AUDIO_TRANSCRIPTIONS_API_URL"
            ],
            "GENERATED_STT_AUDIO_TRANSCRIPTIONS_API_KEY": os.environ[
                "GENERATED_STT_AUDIO_TRANSCRIPTIONS_API_KEY"
            ],
            "LLM_CHAT_COMPLETIONS_API_URL": os.environ[
                "LLM_CHAT_COMPLETIONS_API_URL"
            ],
            "GENERATED_LLM_CHAT_COMPLETIONS_API_KEY": os.environ[
                "GENERATED_LLM_CHAT_COMPLETIONS_API_KEY"
            ],
            "TTS_AUDIO_SPEECH_API_URL": os.environ[
                "TTS_AUDIO_SPEECH_API_URL"
            ],
            "GENERATED_VOICE_WORKER_AUTH_TOKEN": os.environ[
                "GENERATED_VOICE_WORKER_AUTH_TOKEN"
            ],
            "GENERATED_TTS_AUDIO_SPEECH_API_KEY": os.environ[
                "GENERATED_TTS_AUDIO_SPEECH_API_KEY"
            ],
        }
    )
)


@asgi(
    name="workers-voice-realtime-session",
    image=image,
    cpu=2,
    memory="4Gi",
    concurrent_requests=10,
    keep_warm_seconds=10,
    timeout=120,
    authorized=False,
    secrets=[],
    autoscaler=QueueDepthAutoscaler(max_containers=1, min_containers=0),
)
def generate(context):
    del context
    return build_app()
