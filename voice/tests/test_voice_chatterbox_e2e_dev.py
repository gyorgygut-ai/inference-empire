import os

import pytest

WS_URL = os.environ.get("VOICE_CHATTERBOX_URL")


@pytest.mark.skipif(WS_URL is None, reason="VOICE_CHATTERBOX_URL not set (need `beam deploy`)")
def test_dev_e2e_reachable():
    import requests

    resp = requests.get(f"{WS_URL}/v1/audio/voices", timeout=10)
    assert resp.status_code == 200
    data = resp.json()
    assert "voices" in data
