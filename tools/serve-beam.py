"""Serve a Beam worker via the Python SDK and upsert its live URL.

Usage: serve-beam.py <project> <dev|deploy>

Resolves apps/<model>/worker_beam_*.py, loads it as __mp_main__ (same as
the beam CLI so the serve container resolves the handler), prepares the
serve stub, reads the invocation URL from print_invocation_snippet's
return value (no CLI stdout parsing), upserts BEAM_WORKER_URL with
tools/orchestration/upsert-artifact.ts, then attaches to the serve
container (blocks; nx continuous target).
"""

from __future__ import annotations

import os
import runpy
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
        fail("usage: serve-beam.py <project> <dev|deploy> <target>")

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

    from beta9.abstractions.base.runner import (
        ASGI_SERVE_STUB_TYPE,
        ENDPOINT_SERVE_STUB_TYPE,
        TASKQUEUE_SERVE_STUB_TYPE,
    )

    ns = runpy.run_path(os.path.join(worker_dir, files[0]), run_name="__mp_main__")
    served = ns.get("dispatch", ns.get("worker"))
    if served is None:
        fail("worker exposes neither dispatch nor worker entrypoint")
    parent = served.parent
    if hasattr(parent, "taskqueue_stub"):
        stub_type = TASKQUEUE_SERVE_STUB_TYPE
    elif getattr(parent, "is_asgi", None):
        stub_type = ASGI_SERVE_STUB_TYPE
    else:
        stub_type = ENDPOINT_SERVE_STUB_TYPE

    if not parent.prepare_runtime(func=served.func, stub_type=stub_type, force_create_stub=True):
        fail("prepare_runtime failed")
    snippet = parent.print_invocation_snippet()
    url = (getattr(snippet, "url", "") or "").strip()
    if not url:
        fail("no invocation URL issued")
    print(f"[serve-beam] {url}", flush=True)
    upsert_artifact(project, configuration, url)
    served._serve(dir=os.getcwd(), timeout=0)


if __name__ == "__main__":
    main()
