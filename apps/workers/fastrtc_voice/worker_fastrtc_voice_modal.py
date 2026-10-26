"""Modal entry: fastrtc voice proof worker. No GPU, no model loading.

Level 1 runs this file locally via ``modal run ...::serve``.
Level 2 deploys the same class as an ASGI app.
"""
from __future__ import annotations

import modal
import uvicorn
from shared.worker_fastrtc_voice import (
    CONCURRENCY_LIMIT,
    ENV_FILE,
    IMAGE_PIP_DEPS,
    build_app,
    load_local_env,
)

app = modal.App("fastrtc-voice-worker")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(*IMAGE_PIP_DEPS)
    .add_local_python_source("shared")
)


@app.cls(
    image=image,
    gpu=None,
    cpu=4,
    secrets=[modal.Secret.from_dotenv(ENV_FILE)],
    timeout=900,
    scaledown_window=60,
    max_containers=1,
)
@modal.concurrent(max_inputs=CONCURRENCY_LIMIT * 2)
class FastrtcVoiceWorker:
    @modal.asgi_app()
    def web(self) -> object:
        return build_app()


@app.local_entrypoint()
def serve(port: int = 8765) -> None:
    """Run the real app on this machine: same routes, no container, no GPU."""
    load_local_env()
    uvicorn.run(build_app(), host="127.0.0.1", port=port, log_level="info")
