from beam import Image, asgi
from fakes.shared.worker_llm_chat_completions import build_app

image = Image(python_version="python3.11").add_python_packages(
    ["fastapi==0.141.1"]
)


@asgi(
    name="worker-llm-local-stub",
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
