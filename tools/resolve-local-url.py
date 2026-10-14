#!/usr/bin/env python3

"""Resolve local development URLs to production URLs.

Usage: resolve-local-url.py <artifact_path> <configuration>

Reads the artifact file (e.g., MODAL_WORKER_URL, BEAM_WORKER_URL, etc.)
and resolves the local/dev URL to a production/https URL suitable for artifact storage.

Configuration can be 'dev' or 'deploy'.

The resolution logic depends on the URL scheme:
- Local http/https URLs are resolved to https URLs
- Modal URLs on modal.run are kept as-is
- Other patterns are handled based on configuration
"""

import os
import sys
import re

DEFAULT_TIMEOUT_SECONDS = 300


def fail(msg: str) -> "NoReturn":
    print(f"[resolve-local-url] {msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if len(sys.argv) < 3:
        fail("usage: resolve-local-url.py <artifact_path> <configuration> [timeout_seconds]")

    artifact_path = sys.argv[1]
    configuration = sys.argv[2]
    timeout = int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_TIMEOUT_SECONDS

    if configuration not in ("dev", "deploy"):
        fail("configuration must be 'dev' or 'deploy'")

    # Read artifact
    try:
        with open(artifact_path, "r", encoding="utf-8") as f:
            artifact_content = f.read().strip()
    except Exception as e:
        fail(f"could not read artifact file: {e}")

    if not artifact_content:
        fail("artifact file is empty")

    url = artifact_content

    # URL resolution logic
    # Modal URLs (modal.run) keep as-is
    modal_pattern = r"^https://[^/]+\.modal\.run"
    if re.match(modal_pattern, url):
        # Modal production URLs are already https, output as-is
        print(url)
        return

    # Local development URLs need resolution
    # For dev configuration, output the URL with http scheme
    # For deploy configuration, resolve to https
    if configuration == "dev":
        # Keep as-is (local http URL)
        print(url)
    else:
        # Deploy configuration - resolve to https
        if url.startswith("http://"):
            url = url.replace("http://", "https://", 1)
        elif not url.startswith("https://"):
            # Add https if missing
            url = "https://" + url.lstrip("/")
        print(url)


if __name__ == "__main__":
    main()