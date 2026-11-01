"""Acceptance test for worker-vision.

Runs after deploy-beam; proves the deployed worker serves a request.
"""
import base64
import io
import os
import time

from beta9.client.client import Client
from beta9.client.deployment import Deployment
from PIL import Image


def test_worker_vision_acceptance_e2e():
    """Run vision inference and assert its structured result contract."""
    img = Image.new("RGB", (8, 8), (0, 255, 0))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    image_b64 = base64.b64encode(buffer.getvalue()).decode()
    payload = {"image_base64": image_b64}
    url = os.environ["SECRET_WORKER_VISION_URL"]
    token = os.environ["SECRET_BEAM_TOKEN"]
    client = Client(token=token, api_url="https://app.beam.cloud")
    deployment = Deployment(
        base_url=client.base_url,
        token=token,
        workspace_id=client.workspace_id,
        deployment_url=url,
    )
    task = deployment.submit(input=payload)
    assert hasattr(task, "status"), task

    deadline = time.monotonic() + 90
    while not task.is_complete() and time.monotonic() < deadline:
        time.sleep(5)
    assert task.is_complete(), "Timed out waiting 90 seconds for Vision cold load/inference"
    assert str(task.status()) == "COMPLETE"

    result = task.result()
    assert isinstance(result, dict), result
    assert isinstance(result["classification"], str)
    assert isinstance(result["subjects"], list)
    assert isinstance(result["description"], str)
