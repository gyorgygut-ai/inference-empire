import os

import pytest

WS_URL = os.environ.get("VOICE_OPENVOICE_URL")


@pytest.mark.skipif(WS_URL is None, reason="VOICE_OPENVOICE_URL not set (need `beam deploy`)")
def test_dev_e2e_reachable():
    import websockets  # noqa: F401

    assert WS_URL.startswith("ws://") or WS_URL.startswith("wss://")
