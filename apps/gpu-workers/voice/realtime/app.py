"""Shared FastAPI app for the voice worker (Beam + local).

Extracted from the Beam handler so ``scripts/run_local.py`` can serve the exact
same ``/v1/realtime`` route without importing Beam at all.
"""

from __future__ import annotations

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from apps.gpu_workers.voice.realtime.session import Session


def build_app(models: dict, voices_config: dict | None, default_voice: str = "GutAI"):
    """Build the FastAPI app exposing ``/v1/realtime``.

    Shared by the Beam worker (``realtime_voice_qwen.worker``) and the local
    entrypoint (``scripts/run_local.py``) so the wire route never drifts.
    """
    app = FastAPI()

    @app.websocket("/v1/realtime")
    async def realtime_ws(websocket: WebSocket):
        await websocket.accept()
        session = Session(
            models,
            send=websocket.send_text,
            voices_config=voices_config,
            default_voice=default_voice,
        )
        await session.start()
        try:
            while True:
                raw = await websocket.receive_text()
                await session.handle_message(raw)
        except WebSocketDisconnect:
            await session.close()
        except Exception:  # noqa: BLE001
            await session.close()

    return app
