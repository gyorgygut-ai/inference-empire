"""Fastrtc voice worker app: WebRTC signaling + dummy proof protocol.

Level 1/2 proof surface: no GPU, no models, no downloads. Inbound audio
frames are logged, outbound audio is a fixed sine tone. Level 3 replaces
the dummy handler with VAD + STT + LLM + TTS.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import gradio as gr
import httpx
import numpy as np
from dotenv import load_dotenv
from fastrtc import Stream
from fastrtc.tracks import AsyncStreamHandler
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)

TONE_HZ = 440.0
TONE_AMPLITUDE = 0.15
KEEPALIVE_TICK_S = 2.0
LOG_EVERY_FRAMES = 50
CONCURRENCY_LIMIT = 2


def _find_env_file() -> Path:
    """Workspace ``.env``; absent inside provider containers, which use secrets."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / ".env"
        if candidate.is_file():
            return candidate
    return here.parent / ".env"


ENV_FILE = _find_env_file()
TURN_CREDENTIALS_URL = "https://fastrtc-turn-service.hf.space/credentials"
TURN_TTL_SECONDS = 86400
CONNECT_TIMEOUT_S = 10.0
STUN_SERVER = {"urls": "stun:stun.l.google.com:19302"}

IMAGE_PIP_DEPS = [
    "fastrtc==0.0.34",
    "aiortc==1.15.0",
    "av==17.1.0",
    "fastapi==0.141.1",
    "httpx==0.28.1",
    "numpy==2.4.6",
    "python-dotenv==1.2.4",
    "uvicorn[standard]==0.52.4",
]


def load_local_env() -> None:
    """Local runs read the workspace ``.env``; containers get the same values as secrets."""
    load_dotenv(ENV_FILE)


async def rtc_ice_servers() -> list[dict[str, Any]]:
    """Browser-format ``iceServers``: STUN always, TURN minted via ``HF_TOKEN``."""
    servers: list[dict[str, Any]] = [dict(STUN_SERVER)]
    token = os.getenv("HF_TOKEN")
    if not token:
        logger.warning("HF_TOKEN not set; using STUN-only ICE configuration")
        return servers

    try:
        async with httpx.AsyncClient(timeout=CONNECT_TIMEOUT_S) as client:
            response = await client.get(
                TURN_CREDENTIALS_URL,
                headers={"Authorization": f"Bearer {token}"},
                params={"ttl": TURN_TTL_SECONDS},
            )
            response.raise_for_status()
            minted = response.json().get("iceServers", [])
    except httpx.HTTPError as exc:
        logger.warning("rtc: TURN mint failed (%s); STUN-only", exc)
        return servers

    if minted:
        servers.extend(minted)
        logger.info("rtc: STUN + %d TURN server(s) minted", len(minted))
    else:
        logger.warning("rtc: TURN mint returned no servers; STUN-only")
    return servers


class DummyProofHandler(AsyncStreamHandler):
    """Proof handler: log inbound frames, emit a fixed sine tone.

    No VAD, no STT, no TTS, no LLM. ``emit`` is pulled ~50x/s by the output
    track, so the tone plays continuously for the whole session.
    """

    def __init__(self) -> None:
        super().__init__(
            expected_layout="mono",
            output_sample_rate=24000,
            input_sample_rate=48000,
        )
        self.frames = 0
        self.samples = 0
        self.started_at = time.time()

    async def receive(self, frame: tuple[int, np.ndarray]) -> None:
        sample_rate, audio = frame
        self.frames += 1
        self.samples += int(audio.size)
        if self.frames == 1 or self.frames % LOG_EVERY_FRAMES == 0:
            logger.info(
                "inbound frame %d: %d samples @ %d Hz (%.1fs of session)",
                self.frames,
                int(audio.size),
                sample_rate,
                time.time() - self.started_at,
            )

    async def emit(self) -> tuple[int, np.ndarray]:
        t = np.arange(self.output_frame_size) / self.output_sample_rate
        tone = (TONE_AMPLITUDE * np.sin(2 * np.pi * TONE_HZ * t)).astype(np.float32)
        return self.output_sample_rate, tone

    def copy(self) -> DummyProofHandler:
        """Fresh per-connection state (fastrtc calls ``copy`` per peer)."""
        return DummyProofHandler()


def build_app() -> FastAPI:
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    stream = Stream(
        DummyProofHandler(),
        mode="send-receive",
        modality="audio",
        concurrency_limit=CONCURRENCY_LIMIT,
        rtc_configuration=rtc_ice_servers,
    )

    app = FastAPI(title="fastrtc-voice-worker", docs_url=None, redoc_url=None)

    @app.get("/healthz")
    async def healthz() -> dict[str, Any]:
        return {"status": "ok", "mode": "proof", "models": []}

    @app.get("/rtc-configuration")
    async def rtc_configuration() -> JSONResponse:
        # ``rtc_ice_servers`` degrades to STUN-only on mint failure, so this
        # always answers 200 with a usable configuration.
        return JSONResponse({"iceServers": await rtc_ice_servers()})

    @app.get("/keepalive/{webrtc_id}", response_model=None)
    async def keepalive(webrtc_id: str, request: Request):
        if webrtc_id not in stream.connections:
            return JSONResponse({"error": "unknown_connection"}, status_code=404)

        async def event_stream() -> AsyncIterator[bytes]:
            # In-flight for the session's lifetime: the platform counts this
            # request as activity, so the container cannot scale down
            # mid-session. Closes when fastrtc cleans the connection up.
            while webrtc_id in stream.connections and not await request.is_disconnected():
                yield f"event: alive\ndata: {time.time():.0f}\n\n".encode()
                await asyncio.sleep(KEEPALIVE_TICK_S)

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    stream.mount(app)
    app = gr.mount_gradio_app(app, stream.ui, path="/")
    return app
