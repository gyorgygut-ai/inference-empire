"""Modal local platform: starts HTTP mock server for local E2E tests."""
from __future__ import annotations

import threading

import uvicorn

from workers.mock_server.modal import fake as _fake

_SERVER = None
_THREAD = None
PORT = 9002


def _run_server():
    uvicorn.run(_fake.app, host="127.0.0.1", port=PORT, log_level="error")


class LocalModalPlatform:
    def deploy(self):
        global _SERVER, _THREAD
        _fake.clear()
        _THREAD = threading.Thread(target=_run_server, daemon=True)
        _THREAD.start()

    def undeploy(self):
        global _SERVER, _THREAD
        _SERVER = None
        _THREAD = None
        _fake.clear()
