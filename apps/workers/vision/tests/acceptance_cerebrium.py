"""Send a real image inference request to the deployed Cerebrium worker."""

from __future__ import annotations

import base64
import io
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image
from shared.worker_vision import SmallVisionOutput


def main() -> None:
    image = Image.new("RGB", (32, 32), (0, 255, 0))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    payload = json.dumps(
        {"image_base64": base64.b64encode(buffer.getvalue()).decode("ascii")}
    ).encode("utf-8")

    project_id = os.environ["CEREBRIUM_PROJECT_ID"]
    token = os.environ["SECRET_CEREBRIUM_SERVICE_ACCOUNT_TOKEN"]
    request = Request(
        f"https://api.cerebrium.ai/v4/{project_id}/worker-vision/generate",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=900) as response:
        envelope = json.load(response)

    result = SmallVisionOutput.model_validate(envelope["result"]).model_dump()
    output_path = Path("apps/workers/vision/dist/cerebrium-response.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"response": result, "saved_to": str(output_path)}, indent=2))


if __name__ == "__main__":
    main()
