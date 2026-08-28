import os

import pytest

WS_URL = os.environ.get("H3_FL2VA_BEAM_TQ_URL")


@pytest.mark.skipif(WS_URL is None, reason="H3_FL2VA_BEAM_TQ_URL not set (need `beam deploy`)")
def test_dev_e2e_reachable():
    import requests

    resp = requests.get(f"{WS_URL}/health", timeout=10)
    assert resp.status_code == 200
