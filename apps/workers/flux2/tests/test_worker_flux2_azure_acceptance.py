import io
import json
import os
import urllib.request

import pytest
from PIL import Image


@pytest.mark.skipif(
    not os.environ.get("AZURE_WORKER_FLUX2_URL"),
    reason="Azure acceptance runs only after Azure deployment",
)
def test_azure_generate_returns_downloadable_image():
    base_url = os.environ["AZURE_WORKER_FLUX2_URL"].rstrip("/")
    with urllib.request.urlopen(f"{base_url}/health", timeout=30) as response:
        assert response.status == 200

    request = urllib.request.Request(
        f"{base_url}/generate",
        data=json.dumps(
            {
                "prompt": "a red square",
                "width": 256,
                "height": 256,
                "num_inference_steps": 4,
                "guidance_scale": 1.0,
                "seed": 7,
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=900) as response:
        assert response.status == 200
        result = json.loads(response.read())
    artifact_url = result["artifact"]["presigned_url"]

    with urllib.request.urlopen(artifact_url, timeout=60) as response:
        assert response.status == 200
        assert response.headers.get("Content-Type", "").startswith("image/")
        with Image.open(io.BytesIO(response.read())) as artifact:
            artifact.verify()
