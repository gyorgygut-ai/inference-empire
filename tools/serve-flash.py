#!/usr/bin/env python3

"""Serve a Flash worker via the Flash CLI and output its live URL.

Usage: serve-flash.py <worker_script_path> [dev|deploy]

Runs `flash run` in apps/<model>, scans stdout for the endpoint URL,
outputs URL to stdout, then blocks on the child (nx continuous target).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

URL_PATTERN = re.compile(r"https://[^\s'\"`]+")


def fail(msg: str) -> "NoReturn":
    print(f"[serve-flash] {msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if len(sys.argv) < 2:
        fail("usage: serve-flash.py <worker_script_path> [dev|deploy]")

    worker_script = sys.argv[1]
    configuration = sys.argv[2] if len(sys.argv) > 2 else "dev"

    child = subprocess.Popen(
        ["flash", "run", worker_script],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    for line in child.stdout:
        print(line, end="", flush=True)

    child.wait()


if __name__ == "__main__":
    main()