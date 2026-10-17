#!/usr/bin/env python3

"""Serve a Beam worker via the CLI and output its live URL.

Usage: serve-beam.py <worker_beam.py>
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from typing import NoReturn

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

URL_PATTERN = re.compile(r"https://[^\s'\"`]+")


def fail(msg: str) -> NoReturn:
    print(f"[serve-beam] {msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if len(sys.argv) < 2:
        fail("usage: serve-beam.py <worker_beam.py>")

    worker_script = sys.argv[1]

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

    url = None
    if child.stdout is None:
        fail("failed to capture beam output")
    for line in child.stdout:
        sys.stderr.write(line)
        if url is None:
            found = URL_PATTERN.search(line)
            if found:
                url = found.group(0)
                print(url, flush=True)

    child.wait()
    if child.returncode != 0 or url is None:
        fail(f"beam serve failed (code={child.returncode}, url={url})")


if __name__ == "__main__":
    main()
