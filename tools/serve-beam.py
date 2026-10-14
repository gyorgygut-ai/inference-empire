#!/usr/bin/env python3

"""Serve a Beam worker via the CLI and output its live URL.

Usage: serve-beam.py <worker_script_path> [dev|deploy]

Resolves apps/<model>/worker_beam_*.py, spawns `beam serve <file>:<handler>`,
scans stdout/stderr for the invocation URL (no CLI stdout parsing),
outputs URL to stdout, then holds the serve session until terminated (nx continuous target).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def fail(msg: str) -> "NoReturn":
    print(f"[serve-beam] {msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if len(sys.argv) < 2:
        fail("usage: serve-beam.py <worker_script_path> [dev|deploy]")

    worker_script = sys.argv[1]
    configuration = sys.argv[2] if len(sys.argv) > 2 else "dev"

    if configuration not in ("dev", "deploy"):
        fail("configuration must be 'dev' or 'deploy'")

    try:
        with open(worker_script) as f:
            content = f.read()
    except Exception as e:
        fail(f"could not read worker script: {e}")

    match = re.search(r"@task_queue\([\s\S]*?\)\s*\n\s*def\s+(\w+)", content)
    if not match:
        fail("could not find @task_queue handler function")
    handler_name = match.group(1)

    child = subprocess.Popen(
        ["beam", "serve", f"{worker_script}:{handler_name}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    for line in child.stdout:
        print(line, end="", flush=True)

    child.wait()
    if child.returncode != 0:
        fail(f"beam serve exited with code {child.returncode}")


if __name__ == "__main__":
    main()