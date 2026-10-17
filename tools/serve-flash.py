#!/usr/bin/env python3

"""Serve a Flash worker via the Flash CLI and output its live URL.

Usage: serve-flash.py <worker_flash.py>
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
    print(f"[serve-flash] {msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if len(sys.argv) < 2:
        fail("usage: serve-flash.py <worker_flash.py>")

    worker_script = sys.argv[1]

    child = subprocess.Popen(
        ["flash", "run", worker_script],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    url = None
    if child.stdout is None:
        fail("failed to capture flash output")
    for line in child.stdout:
        sys.stderr.write(line)
        if url is None:
            found = URL_PATTERN.search(line)
            if found:
                url = found.group(0)
                print(url, flush=True)

    child.wait()
    if child.returncode != 0 or url is None:
        fail(f"flash run failed (code={child.returncode}, url={url})")


if __name__ == "__main__":
    main()
