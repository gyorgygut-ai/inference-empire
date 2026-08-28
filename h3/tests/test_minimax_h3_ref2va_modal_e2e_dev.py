import os

import pytest

WS_URL = os.environ.get("H3_REF2VA_MODAL_URL")


@pytest.mark.skipif(WS_URL is None, reason="H3_REF2VA_MODAL_URL not set (need `modal deploy`)")
def test_dev_e2e_reachable():
    import requests

    resp = requests.get(f"{WS_URL}/health", timeout=10)
    assert resp.status_code == 200
