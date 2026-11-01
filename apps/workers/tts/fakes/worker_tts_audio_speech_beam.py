from beam import Image, asgi
from fakes.shared.worker_tts_audio_speech import build_app

image = Image(python_version="python3.11").add_python_packages(
    ["fastapi==0.141.1", "numpy==1.26.4"]
)


@asgi(
    name="worker-tts-local-stub",
    image=image,
    cpu=1,
    memory="1Gi",
    concurrent_requests=4,
    authorized=False,
    secrets=[],
)
def generate(context):
    del context
    return build_app()


app = build_app()
