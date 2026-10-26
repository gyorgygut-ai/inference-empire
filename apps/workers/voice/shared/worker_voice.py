"""Voice worker app: TURN credentials, WebRTC signaling, dummy proof protocol."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from shared.proof_engine import ProofPeer, rtc_ice_servers

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)

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
ICE_GATHERING_TIMEOUT_S = 5.0
CONNECT_TIMEOUT_S = 30.0

IMAGE_PIP_DEPS = [
    "aiortc==1.15.0",
    "av==17.1.0",
    "fastapi==0.141.1",
    "httpx==0.28.1",
    "numpy==2.4.6",
    "python-dotenv==1.2.4",
    "uvicorn[standard]==0.52.4",
]


class MissingHFTokenError(RuntimeError):
    """``HF_TOKEN`` is not present in the environment."""


def load_local_env() -> None:
    """Local runs read the workspace ``.env``; containers get the same values as secrets."""
    load_dotenv(ENV_FILE)


async def turn_ice_servers(ttl: int = TURN_TTL_SECONDS) -> dict[str, Any]:
    """Mint TURN credentials from the HF proxy using the existing ``HF_TOKEN``."""
    token = os.getenv("HF_TOKEN")
    if not token:
        raise MissingHFTokenError("HF_TOKEN is not set")

    async with httpx.AsyncClient(timeout=CONNECT_TIMEOUT_S) as client:
        response = await client.get(
            TURN_CREDENTIALS_URL,
            headers={"Authorization": f"Bearer {token}"},
            params={"ttl": ttl},
        )
        response.raise_for_status()
        return response.json()


def is_sdp_offer(sdp: str) -> bool:
    """Cheap structural check so a malformed offer answers 400, not a hang."""
    required = ("v=0", "m=audio", "a=ice-ufrag:", "a=ice-pwd:")
    return all(line in sdp for line in required)


def build_app() -> FastAPI:
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    peers: dict[str, ProofPeer] = {}

    def _release(peer_id: str) -> None:
        if peers.pop(peer_id, None) is not None:
            logger.info("released peer %s", peer_id)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        for peer in list(peers.values()):
            await peer.close()
        peers.clear()

    app = FastAPI(title="voice-worker", lifespan=lifespan, docs_url=None, redoc_url=None)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "ok", "mode": "proof", "models": []}

    @app.get("/turn-credentials")
    async def turn_credentials() -> Response:
        try:
            return JSONResponse(await turn_ice_servers())
        except MissingHFTokenError as exc:
            return JSONResponse({"error": str(exc)}, status_code=503)
        except httpx.HTTPError as exc:
            return JSONResponse(
                {"error": f"turn credentials unavailable: {exc}"}, status_code=502
            )

    @app.post("/v1/realtime/calls")
    async def create_call(request: Request) -> Response:
        media_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
        if media_type != "application/sdp":
            return JSONResponse({"error": "unsupported_media_type"}, status_code=415)

        offer = (await request.body()).decode("utf-8", "replace")
        if not is_sdp_offer(offer):
            return JSONResponse({"error": "invalid_sdp"}, status_code=400)

        try:
            credentials = await turn_ice_servers()
        except MissingHFTokenError as exc:
            return JSONResponse({"error": str(exc)}, status_code=503)
        except httpx.HTTPError as exc:
            return JSONResponse(
                {"error": f"turn credentials unavailable: {exc}"}, status_code=502
            )

        peer = ProofPeer(rtc_ice_servers(credentials))
        peer.on_release = _release
        try:
            answer = await peer.answer(offer, ICE_GATHERING_TIMEOUT_S)
        except Exception:
            await peer.close()
            raise

        peers[peer.id] = peer
        return Response(
            content=answer,
            media_type="application/sdp",
            status_code=201,
            headers={"Location": f"/v1/realtime/calls/{peer.id}"},
        )

    return app
