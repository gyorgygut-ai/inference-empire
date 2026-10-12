"""Serve a Modal worker via the Python SDK and upsert its live URL.

Usage: serve-modal.py <project> <dev|deploy>

Resolves apps/<model>/worker_modal_*.py, enters modal.serving.serve_app,
reads the web URL programmatically via get_web_url (no stdout parsing),
upserts MODAL_WORKER_URL with tools/orchestration/upsert-artifact.ts, then holds
the serve session until terminated (nx continuous target).
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def fail(msg: str) -> "NoReturn":
    print(f"[serve-modal] {msg}", file=sys.stderr)
    raise SystemExit(1)


def upsert_artifact(project: str, configuration: str, url: str) -> None:
    tsx = os.path.join(ROOT, "node_modules", ".bin", "tsx")
    cmd = [tsx, "tools/orchestration/upsert-artifact.ts"] if os.path.isfile(tsx) else ["npx", "tsx", "tools/orchestration/upsert-artifact.ts"]
    result = subprocess.run(
        [*cmd, project, configuration, f"MODAL_WORKER_URL={url}"],
        cwd=ROOT,
    )
    if result.returncode != 0:
        fail("upsert-artifact failed")


def main() -> None:
    if len(sys.argv) != 3:
        fail("usage: serve-modal.py <project> <dev|deploy>")
    project, configuration = sys.argv[1], sys.argv[2]
    if configuration not in ("dev", "deploy"):
        fail("usage: serve-modal.py <project> <dev|deploy> <target>")

    model = project.removeprefix("worker-").replace("-", "_")
    worker_dir = os.path.join(ROOT, "apps", model)
    try:
        files = [
            f for f in os.listdir(worker_dir)
            if f.startswith("worker_modal_") and f.endswith(".py")
        ]
    except OSError:
        files = []
    if len(files) != 1:
        fail(f"expected exactly one worker_modal_*.py in apps/{model}, found {len(files)}")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from modal.cli.import_refs import import_app_from_ref, parse_import_ref
        from modal.serving import serve_app

        ref = parse_import_ref(f"apps/{model}/{files[0]}", command="serve-modal")
        app = import_app_from_ref(ref, base_cmd="serve-modal")
        with serve_app(app, ref):
            urls: dict[str, str] = {}
            for tag, fn in (app.registered_functions or {}).items():
                try:
                    url = fn.get_web_url() or ""
                except Exception:
                    url = ""
                if url:
                    urls[tag] = url
                    print(f"[serve-modal] {tag} => {url}", flush=True)
            if not urls:
                fail("no web URL issued (worker needs a fastapi_endpoint/asgi_app)")
            url = urls.get("generate_web") or sorted(urls.values())[0]
            upsert_artifact(project, configuration, url)
            print(f"[serve-modal] serving {project} (Ctrl-C to stop)", flush=True)
            threading.Event().wait()


if __name__ == "__main__":
    main()
