"""Beam entry: WebRTC voice proof worker. No GPU, no model loading.

Beam has no local CLI runner, so Level 1 runs this file directly via its
``__main__`` guard; Level 2 deploys the ``@asgi`` handler.
"""
from __future__ import annotations

import uvicorn
from beam import Image, asgi
from shared.worker_voice import IMAGE_PIP_DEPS, build_app, load_local_env

image = Image(python_version="python3.11").add_python_packages(IMAGE_PIP_DEPS)


@asgi(
    name="voice-proof-worker",
    cpu=1,
    memory="2Gi",
    timeout=600,
    keep_warm_seconds=600,
    concurrent_requests=1,
    image=image,
    secrets=["HF_TOKEN"],
)
def web(context: object) -> object:
    return build_app()


if __name__ == "__main__":
    load_local_env()
    uvicorn.run(build_app(), host="127.0.0.1", port=8765, log_level="info")
