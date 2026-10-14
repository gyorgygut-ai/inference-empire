#!/usr/bin/env python3

"""Wait for an artifact file to exist and output its contents.

Usage: wait-for-artifact.py <artifact_path>

Reads the artifact file and outputs its contents to stdout.
Used by the orchestrator's run-injected-command to inject environment variables
from artifacts produced by other targets.

Exits with code 1 if the artifact does not exist after timeout.
"""

import os
import sys
import time

DEFAULT_TIMEOUT_SECONDS = 300


def fail(msg: str) -> "NoReturn":
    print(f"[wait-for-artifact] {msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if len(sys.argv) < 2:
        fail("usage: wait-for-artifact.py <artifact_path> [timeout_seconds]")

    artifact_path = sys.argv[1]
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_TIMEOUT_SECONDS

    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(artifact_path):
            try:
                with open(artifact_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    print(content, flush=True)
                    return
            except Exception:
                pass
        time.sleep(1)

    fail(f"timeout after {timeout}s waiting for artifact: {artifact_path}")


if __name__ == "__main__":
    main()