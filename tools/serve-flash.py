"""Serve a Flash worker via the Flash CLI and upsert its live URL.

Usage: serve-flash.py <project> <dev|deploy>

Runs `flash run` in apps/<model>, scans stdout for the endpoint URL,
upserts FLASH_WORKER_URL with tools/orchestration/upsert-artifact.ts,
then blocks on the child (nx continuous target).
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


def upsert_artifact(project: str, configuration: str, url: str) -> None:
    tsx = os.path.join(ROOT, "node_modules", ".bin", "tsx")
    cmd = [tsx, "tools/orchestration/upsert-artifact.ts"] if os.path.isfile(tsx) else ["npx", "tsx", "tools/orchestration/upsert-artifact.ts"]
    result = subprocess.run(
        [*cmd, project, configuration, f"FLASH_WORKER_URL={url}"],
        cwd=ROOT,
    )
    if result.returncode != 0:
        fail("upsert-artifact failed")


def main() -> None:
    if len(sys.argv) != 3:
        fail("usage: serve-flash.py <project> <dev|deploy>")
    project, configuration = sys.argv[1], sys.argv[2]
    if configuration not in ("dev", "deploy"):
        fail("usage: serve-flash.py <project> <dev|deploy>")

    model = project.removeprefix("worker-").replace("-", "_")
    worker_dir = os.path.join(ROOT, "apps", model)
    if not os.path.isdir(worker_dir):
        fail(f"missing worker dir: apps/{model}")

    child = subprocess.Popen(
        ["uv", "run", "--locked", "flash", "run"],
        cwd=worker_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert child.stdout is not None
    seen: str | None = None
    for line in child.stdout:
        print(line, end="", flush=True)
        if seen is None:
            match = URL_PATTERN.search(line)
            if match:
                seen = match.group(0)
                upsert_artifact(project, configuration, seen)
    code = child.wait()
    if seen is None:
        fail("no endpoint URL in flash run output")
    raise SystemExit(code)


if __name__ == "__main__":
    main()
