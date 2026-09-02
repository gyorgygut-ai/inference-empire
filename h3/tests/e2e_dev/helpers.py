"""Reusable helpers for E2E dev tests — deploy, undeploy, artifact verification."""
import io
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import requests


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

def deploy_beam_fl2va() -> tuple[str, str, str]:
    """Deploy Beam fl2va comfy worker. Returns (deployment_id, endpoint_url, auth_token)."""
    rc, output = _run(
        ["beam", "deploy", "worker_beam_tq_minimax_h3_ref2va_comfy.py:generate"],
        cwd=WORKER_DIR, timeout=600,
    )
    if rc != 0:
        raise RuntimeError(f"beam deploy failed (rc={rc})")
    _, list_output = _run(["beam", "deployment", "list"], cwd=WORKER_DIR, timeout=30)
    deployment_id = _parse_beam_deployment_id(list_output, "minimax-h3-")
    endpoint_url, auth_token = _parse_beam_endpoint(output)
    return deployment_id, endpoint_url, auth_token


def undeploy_beam(deployment_id: str):
    _run(["beam", "deployment", "delete", deployment_id], cwd=WORKER_DIR, timeout=60)


def call_beam_fl2va(input_data: dict, endpoint_url: str, auth_token: str) -> dict:
    """Call deployed Beam task queue via HTTP."""
    resp = requests.post(
        endpoint_url,
        headers={
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        },
        json=input_data,
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()


def deploy_flash_comfy() -> None:
    """Deploy Flash comfy worker."""
    rc, output = _run(
        ["flash", "deploy"],
        cwd=WORKER_DIR, timeout=600,
    )
    if rc != 0:
        raise RuntimeError(f"flash deploy failed (rc={rc})")


def undeploy_flash_comfy():
    _run(["flash", "undeploy"], cwd=WORKER_DIR, timeout=60)


def call_flash_comfy(input_data: dict) -> dict:
    """Call deployed Flash comfy worker via runpod_flash SDK."""
    import runpod_flash as rf
    endpoint = rf.Endpoint(name="minimax-h3-comfy-worker")
    return endpoint.runsync(input_data)


# --- Artifact verification ---

def verify_artifact_video(url: str):
    """Download artifact from signed URL, validate it's a real MP4 video."""
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    content = resp.content
    assert len(content) > 100, f"Video too small ({len(content)} bytes), likely invalid"
    # MP4 magic bytes: ftyp at offset 4
    assert content[4:8] == b"ftyp", f"Not a valid MP4 (missing ftyp header): {content[:20]!r}"
    return content


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


def _parse_beam_endpoint(deploy_output: str) -> tuple[str, str]:
    """Parse endpoint URL and auth token from beam deploy output."""
    url_match = re.search(r"curl -X POST '([^']+)'", deploy_output)
    token_match = re.search(r"Authorization: Bearer (\S+)", deploy_output)
    if not url_match or not token_match:
        raise RuntimeError("Could not parse beam endpoint from deploy output")
    return url_match.group(1), token_match.group(1)
