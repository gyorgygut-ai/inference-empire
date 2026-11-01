"""Acceptance test for worker-flux2.

Runs after deploy-beam; proves the deployed worker serves a request.
"""
import os
import time
import urllib.request

from beta9.client.client import Client
from beta9.client.deployment import Deployment


def test_worker_flux2_acceptance_e2e():
    """Queue inference on Beam and verify its image artifact is downloadable."""
    url = os.environ["SECRET_WORKER_FLUX2_URL"]
    token = os.environ["SECRET_BEAM_TOKEN"]
    payload = {
        "prompt": "a red square",
        "width": 256,
        "height": 256,
        "num_inference_steps": 4,
        "guidance_scale": 1.0,
        "seed": 7,
    }
    client = Client(token=token, api_url="https://app.beam.cloud")
    deployment = Deployment(
        base_url=client.base_url,
        token=token,
        workspace_id=client.workspace_id,
        deployment_url=url,
    )
    task = deployment.submit(input=payload)
    assert hasattr(task, "status"), task

    deadline = time.monotonic() + 300
    while not task.is_complete() and time.monotonic() < deadline:
        time.sleep(5)
    assert task.is_complete(), "Timed out waiting 300 seconds for Flux2 inference"
    assert str(task.status()) == "COMPLETE"

    result = task.result()
    assert isinstance(result, dict), result
    artifact_url = result["artifact"]["presigned_url"]

    with urllib.request.urlopen(artifact_url, timeout=60) as response:
        assert response.status == 200
        assert response.headers.get("Content-Type", "").startswith("image/")
        assert response.read()
