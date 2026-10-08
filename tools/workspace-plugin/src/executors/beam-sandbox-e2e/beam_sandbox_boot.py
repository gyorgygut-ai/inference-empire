"""Boot a Beam GPU sandbox from a worker family's image and run its Beam e2e inside.

No deploy. Usage: beam_sandbox_boot.py <family> -- <command...>
Env: SANDBOX_TIMEOUT (exec budget, default 600), SANDBOX_GPU (default L4).

Convention: apps/<family>/worker_beam_*.py (exactly one) must export
`image` and optionally CACHE_PATH (default ./hf-cache). Only Beam e2e
files are executed here; Modal/Flash files are excluded by the executor
selector. Sources are staged via sb.fs.upload_file so Modal image
mtimes never enter Beam's ZIP sync path.
"""
from __future__ import annotations

import glob
import os
import sys

sys.path.insert(0, os.getcwd())


def _upload_tree(sb, local_dir: str, remote_dir: str) -> None:
    """Upload local_dir to remote_dir, skipping caches. Follows dir symlinks."""
    skip = {"__pycache__", "node_modules", ".git", "dist", "build", ".venv"}
    for root, dirs, files in os.walk(local_dir, followlinks=True):
        dirs[:] = [d for d in dirs if d not in skip]
        for name in files:
            if name.endswith((".pyc", ".pyo")):
                continue
            local_path = os.path.join(root, name)
            rel = os.path.relpath(local_path, local_dir)
            remote_path = f"{remote_dir}/{rel}".replace(os.sep, "/")
            parent = "/".join(remote_path.split("/")[:-1])
            try:
                sb.fs.create_directory(parent)
            except Exception:
                pass
            sb.fs.upload_file(local_path, remote_path)


def _stage_file(sb, local_path: str, remote_path: str) -> None:
    parent = "/".join(remote_path.split("/")[:-1])
    try:
        sb.fs.create_directory(parent)
    except Exception:
        pass
    sb.fs.upload_file(local_path, remote_path)


def main() -> int:
    family = sys.argv[1]
    rest = sys.argv[2:]
    cmd = rest[1:] if rest and rest[0] == "--" else rest
    timeout_s = int(os.environ.get("SANDBOX_TIMEOUT", "600"))
    gpu = os.environ.get("SANDBOX_GPU", "L4")

    from beam import Sandbox, Volume

    mods = glob.glob(f"apps/{family}/worker_beam_*.py")
    assert len(mods) == 1, f"expected one worker_beam file for {family}: {mods}"
    stem = os.path.splitext(os.path.basename(mods[0]))[0]
    worker = __import__(f"apps.{family}.{stem}", fromlist=["image"])
    cache_path = getattr(worker, "CACHE_PATH", "./hf-cache")

    img = worker.image.add_python_packages(["pytest", "httpx", "pillow"])

    env: dict[str, str] = {}
    for key in ("BEAM_TOKEN", "BEAM_CLIENT_ID", "BEAM_CLIENT_SECRET"):
        if os.environ.get(key):
            env[key] = os.environ[key]

    sb = Sandbox(
        cpu=4,
        memory="32Gi",
        gpu=gpu,  # type: ignore[arg-type]
        gpu_count=1,
        image=img,
        volumes=[Volume(name="hf-cache", mount_path=cache_path)],
        env=env,
        keep_warm_seconds=timeout_s + 600,
    ).create()
    try:
        print("Beam sandbox up", flush=True)
        ws = "/workspace"
        if os.path.isfile("apps/__init__.py"):
            _stage_file(sb, "apps/__init__.py", f"{ws}/apps/__init__.py")
        if os.path.isfile("apps/conftest.py"):
            _stage_file(sb, "apps/conftest.py", f"{ws}/apps/conftest.py")
        _upload_tree(sb, f"apps/{family}", f"{ws}/apps/{family}")
        # Full packages tree: families cross-import (e.g. vision -> media).
        # One walk covers shared-gpu symlink + shared-gpu real dir.
        _upload_tree(sb, "packages", f"{ws}/packages")

        probe = sb.process.exec("python", "-c", "import pytest, httpx", cwd=ws)
        probe.wait(timeout=120)
        if probe.status()[0] != 0:
            print("installing test deps", flush=True)
            inst = sb.process.exec(
                "pip", "install", "-q", "pytest", "httpx", "pillow", cwd=ws
            )
            inst.wait(timeout=600)
            if inst.status()[0] != 0:
                print(inst.stderr.read(), flush=True)
                return 1
        proc = sb.process.exec(*cmd, cwd=ws)
        proc.wait(timeout=timeout_s + 60)
        print(proc.stdout.read(), flush=True)
        print(proc.stderr.read(), flush=True)
        return 0 if proc.status()[0] == 0 else 1
    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}", flush=True)
        return 1
    finally:
        sb.terminate()
        print("BEAM_SANDBOX_DONE", flush=True)


if __name__ == "__main__":
    sys.exit(main())
