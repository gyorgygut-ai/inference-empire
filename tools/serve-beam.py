"""Serve a Beam worker via the CLI and upsert its live URL.

Usage: serve-beam.py <project> <dev|deploy>

Resolves apps/<model>/worker_beam_*.py, spawns `beam serve <file>:<handler>`,
scans stdout/stderr for the invocation URL (no CLI stdout parsing),
upserts BEAM_WORKER_URL with tools/orchestration/upsert-artifact.ts, then
holds the serve session until terminated (nx continuous target).
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


def upsert_artifact(project: str, configuration: str, url: str) -> None:
    tsx = os.path.join(ROOT, "node_modules", ".bin", "tsx")
    cmd = [tsx, "tools/orchestration/upsert-artifact.ts"] if os.path.isfile(tsx) else ["npx", "tsx", "tools/orchestration/upsert-artifact.ts"]
    result = subprocess.run(
        [*cmd, project, configuration, f"BEAM_WORKER_URL={url}"],
        cwd=ROOT,
    )
    if result.returncode != 0:
        fail("upsert-artifact failed")


def main() -> None:
    if len(sys.argv) != 3:
        fail("usage: serve-beam.py <project> <dev|deploy>")
    project, configuration = sys.argv[1], sys.argv[2]
    if configuration not in ("dev", "deploy"):
        fail("usage: serve-beam.py <project> <dev|deploy>")

    model = project.removeprefix("worker-").replace("-", "_")
    worker_dir = os.path.join(ROOT, "apps", model)
    try:
        files = [
            f for f in os.listdir(worker_dir)
            if f.startswith("worker_beam_") and f.endswith(".py")
        ]
    except OSError:
        files = []
    if len(files) != 1:
        fail(f"expected exactly one worker_beam_*.py in apps/{model}, found {len(files)}")

    # Read the handler name from the worker file (the @task_queue decorated function)
    handler_name = None
    worker_path = os.path.join(worker_dir, files[0])
    with open(worker_path) as f:
        content = f.read()
    # Find the function decorated with @task_queue (handles multi-line decorator)
    match = re.search(r'@task_queue\([\s\S]*?\)\s*\n\s*def\s+(\w+)', content)
    if match:
        handler_name = match.group(1)
    if not handler_name:
        fail("could not find @task_queue handler function")

    child = subprocess.Popen(
        ["beam", "serve", f"apps/{model}/{files[0]}:{handler_name}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    url_pattern = re.compile(r'https://[^\s\'"`]*\.app\.beam\.cloud[^\s\'"`]*')
    seen_url: str | None = None

    for line in child.stdout:
        print(line, end="", flush=True)
        if seen_url:
            continue
        m = url_pattern.search(line)
        if m:
            seen_url = m[0]
            print(f"[serve-beam] {seen_url}", flush=True)
            upsert_artifact(project, configuration, seen_url)

    child.wait()
    if configuration == "dev" and child.returncode != 0:
        fail(f"beam serve exited with code {child.returncode}")


if __name__ == "__main__":
    main()
