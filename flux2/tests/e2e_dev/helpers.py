"""Reusable helpers for E2E dev tests — deploy, undeploy, artifact verification."""
import io
import os
import re
import subprocess
import time
from pathlib import Path

import requests
from PIL import Image


WORKER_DIR = str(Path(__file__).parent.parent.parent)
REPO_ROOT = str(Path(WORKER_DIR).parent)

# Load .env for credentials
for line in (Path(REPO_ROOT) / ".env").read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, _, value = line.partition("=")
    key, value = key.strip(), value.strip().strip('"').strip("'")
    if key and key not in os.environ:
        os.environ[key] = value

# Subprocess env: bypass proxy to avoid SSL cert failures
_subprocess_env = os.environ.copy()
_subprocess_env["NO_PROXY"] = "*"
_subprocess_env["no_proxy"] = "*"
_subprocess_env["HTTPS_PROXY"] = ""
_subprocess_env["HTTP_PROXY"] = ""
_subprocess_env["REQUESTS_CA_BUNDLE"] = ""
_subprocess_env["SSL_CERT_FILE"] = ""
_subprocess_env["PYTHONHTTPSVERIFY"] = "0"


def _run(cmd, cwd=None, timeout=600):
    """Run command, stream output live to terminal, return (returncode, stdout_text)."""
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, cwd=cwd, env=_subprocess_env,
    )
    lines = []
    for line in proc.stdout:
        print(line, end="", flush=True)
        lines.append(line)
    proc.wait(timeout=timeout)
    return proc.returncode, "".join(lines)


# --- Deploy / undeploy ---

def deploy_beam() -> str:
    """Deploy Beam task queue. Returns deployment_id."""
    rc, output = _run(
        ["beam", "deploy", "worker_beam_tq_flux2_klein9b.py:generate"],
        cwd=WORKER_DIR, timeout=600,
    )
    if rc != 0:
        raise RuntimeError(f"beam deploy failed (rc={rc})")
    _, list_output = _run(["beam", "deployment", "list"], cwd=WORKER_DIR, timeout=30)
    deployment_id = _parse_beam_deployment_id(list_output, "flux2-klein9b-worker")
    return deployment_id


def undeploy_beam(deployment_id: str):
    _run(["beam", "deployment", "delete", deployment_id], cwd=WORKER_DIR, timeout=60)


def call_beam(deployment_id: str, input_data: dict) -> dict:
    """Call deployed Beam task queue via Python SDK."""
    from beam import Client
    client = Client(token=os.environ["BEAM_TOKEN"])
    deployment = client.get_deployment_by_id(deployment_id)
    task = deployment.submit(input=input_data)
    return task.result(wait=True)


def deploy_modal() -> None:
    """Deploy Modal app."""
    rc, output = _run(
        ["modal", "deploy", "worker_modal_cls_flux2_klein9b.py"],
        cwd=REPO_ROOT, timeout=600,
    )
    if rc != 0:
        raise RuntimeError(f"modal deploy failed (rc={rc})")


def undeploy_modal():
    _run(["modal", "app", "stop", "flux2-klein9b-worker", "-y"], cwd=REPO_ROOT, timeout=60)


def call_modal(input_data: dict) -> dict:
    """Call deployed Modal function via Python SDK."""
    import modal
    f = modal.Function.from_name("flux2-klein9b-worker", "FluxKleinWorker.generate_web")
    return f.remote(**input_data)


# --- Artifact verification ---

def verify_artifact(url: str) -> Image.Image:
    """Download artifact from signed URL, validate it's a real image. Returns PIL Image."""
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content))
    assert img.size[0] > 0 and img.size[1] > 0, f"Image has zero dimensions: {img.size}"
    return img


def verify_contract(data: dict):
    """Verify output contract fields."""
    assert "artifact" in data, f"Missing 'artifact' in response: {data}"
    assert data["artifact"]["presigned_url"].startswith("https://"), f"Bad presigned_url: {data['artifact']['presigned_url']}"


def _parse_beam_deployment_id(stdout: str, name: str) -> str:
    for line in stdout.splitlines():
        if name in line:
            parts = line.split()
            if parts:
                return parts[0]
    raise RuntimeError(f"Could not find deployment ID for {name} in: {stdout}")
