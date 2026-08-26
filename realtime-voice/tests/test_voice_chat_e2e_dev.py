import os

import pytest

# Dev E2E requires a running `modal serve worker_voice_chat.py` endpoint.
# Set VOICE_CHAT_WS_URL (ws://...) to run against it; otherwise the suite skips.
WS_URL = os.environ.get("VOICE_CHAT_WS_URL")


@pytest.mark.skipif(WS_URL is None, reason="VOICE_CHAT_WS_URL not set (need `modal serve`)")
def test_dev_e2e_reachable():
    import websockets  # noqa: F401

    assert WS_URL.startswith("ws://") or WS_URL.startswith("wss://")
