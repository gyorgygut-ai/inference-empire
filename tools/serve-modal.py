#!/usr/bin/env python3

import asyncio
import json
import os
import re
import subprocess
import sys
from typing import NoReturn

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fail(msg: str) -> NoReturn:
    print(f"[serve-modal] {msg}", file=sys.stderr)
    raise SystemExit(1)


def stop_stale_ephemerals(app_name: str) -> None:
    try:
        listed = subprocess.run(
            ["uv", "run", "--locked", "modal", "app", "list", "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if listed.returncode != 0:
            print("[serve-modal] warning: app list failed, skipping cleanup", file=sys.stderr, flush=True)
            return
        for app in json.loads(listed.stdout or "[]"):
            if app.get("description") == app_name and app.get("state") == "ephemeral":
                subprocess.run(
                    ["uv", "run", "--locked", "modal", "app", "stop", "--yes", app["app_id"]],
                    cwd=ROOT,
                    capture_output=True,
                    timeout=120,
                )
                print(f"[serve-modal] stopped stale ephemeral {app['app_id']}", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[serve-modal] warning: app list cleanup skipped: {e}", file=sys.stderr, flush=True)


def main() -> None:
    if len(sys.argv) < 2:
        fail("usage: serve-modal.py <worker_modal.py>")

    worker_script = sys.argv[1]

    try:
        worker_content = open(worker_script, encoding="utf-8").read()
    except Exception as e:
        fail(f"could not read worker script: {e}")

    match = re.search(r"modal\.App\s*\(\s*[\"']([^\"']+)[\"']\s*\)", worker_content)
    if not match:
        fail("could not find modal.App name in worker script")
    app_name = match[1]

    stop_stale_ephemerals(app_name)

    try:
        asyncio.run(serve_app(app_name, worker_script))
    except Exception as e:
        fail(f"error running serve_app: {e}")


async def serve_app(app_name: str, worker_script: str) -> None:
    try:
        from modal.cli.import_refs import import_app_from_ref, parse_import_ref
        from modal.serving import serve_app as serve_app_func

        ref = parse_import_ref(worker_script, command="serve-modal")
        app = import_app_from_ref(ref, base_cmd="serve-modal")

        urls = {}
        for tag, fn in app.registered_functions.items():
            try:
                url = fn.get_web_url() or ""
            except Exception:
                url = ""
            if url:
                urls[tag] = url
                print(f"[serve-modal] {tag} => {url}", file=sys.stderr, flush=True)

        if not urls:
            fail("no web URL issued (worker needs a fastapi_endpoint/asgi_app)")

        url = urls.get("generate_web") or sorted(urls.values())[0]
        print(url, flush=True)
        print(f"[serve-modal] serving {app_name} (Ctrl-C to stop)", file=sys.stderr, flush=True)

        async with serve_app_func(app, ref) as _:
            await asyncio.Future()  # Wait indefinitely

    except Exception as e:
        print(f"[serve-modal] error: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
