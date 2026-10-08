"""Boot a Modal GPU sandbox from a worker family's image and run its e2e suite inside.

No deploy. Usage: sandbox_boot.py <family> -- <command...>
Env: SANDBOX_TIMEOUT (exec budget, default 600), SANDBOX_GPU (default L4).

Convention: apps/<family>/worker_modal_cls_*.py (exactly one) must export
`image` and `hf_cache_vol`, and optionally MODEL_MOUNT (default
/root/.cache/huggingface). Non-Python fixtures under
apps/<family>/tests/fixtures/ are staged to their mirrored in-image path
(add_local_python_source only mounts .py files).
"""
from __future__ import annotations

import glob
import os
import sys


def main() -> int:
    family = sys.argv[1]
    rest = sys.argv[2:]
    cmd = rest[1:] if rest and rest[0] == "--" else rest
    timeout_s = int(os.environ.get("SANDBOX_TIMEOUT", "600"))
    gpu = os.environ.get("SANDBOX_GPU", "L4")

    import modal

    mods = glob.glob(f"apps/{family}/worker_modal_cls_*.py")
    assert len(mods) == 1, f"expected one worker_modal_cls file for {family}: {mods}"
    stem = os.path.splitext(os.path.basename(mods[0]))[0]
    worker = __import__(f"apps.{family}.{stem}", fromlist=["image", "hf_cache_vol"])
    mount = getattr(worker, "MODEL_MOUNT", "/root/.cache/huggingface")

    img = worker.image
    for path in sorted(glob.glob(f"apps/{family}/tests/fixtures/*")):
        if os.path.isfile(path):
            img = img.add_local_file(path, f"/root/{path}")

    creds = {}
    for key in (
        "MODAL_TOKEN_ID",
        "MODAL_TOKEN_SECRET",
        "BEAM_TOKEN",
        "BEAM_CLIENT_ID",
        "BEAM_CLIENT_SECRET",
    ):
        if os.environ.get(key):
            creds[key] = os.environ[key]

    app = modal.App.lookup(f"{family}-sandbox", create_if_missing=True)
    sb = modal.Sandbox.create(
        image=img,
        gpu=gpu,
        volumes={mount: worker.hf_cache_vol},
        cpu=4,
        memory=32768,
        timeout=timeout_s * 2 + 600,
        app=app,
        workdir="/root",
        env=creds or None,
    )
    try:
        print("GPU sandbox up", flush=True)
        probe = sb.exec("python", "-c", "import pytest, httpx", timeout=120)
        probe.stdout.read()
        if probe.returncode != 0:
            print("installing test deps", flush=True)
            inst = sb.exec(
                "pip", "install", "-q", "pytest", "httpx", "pillow", "modal", "beam-client",
                timeout=600,
            )
            print(inst.stdout.read(), flush=True)
            if inst.returncode != 0:
                print(inst.stderr.read(), flush=True)
                return 1
        proc = sb.exec(*cmd, timeout=timeout_s)
        out = proc.stdout.read()
        print(out, flush=True)
        print(proc.stderr.read(), flush=True)
        return 0 if proc.returncode == 0 else 1
    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}", flush=True)
        return 1
    finally:
        sb.terminate()
        print("GPU_SANDBOX_DONE", flush=True)


if __name__ == "__main__":
    sys.exit(main())
