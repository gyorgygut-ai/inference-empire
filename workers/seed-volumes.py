"""Seed model volumes from worker-declared deps. No deploy, no inference.

Usage: uv run --locked python workers/seed-volumes.py [--provider modal|beam|all] [--only tiny_sd,flux2] [--dry-run]
"""
from __future__ import annotations

import argparse
import concurrent.futures
import importlib
import re
import shutil
import subprocess
import sys
import tempfile
import warnings
from pathlib import Path

WORKDIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKDIR))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(WORKDIR / ".env")  # HF_TOKEN etc. for gated repos; never commit .env

VOL_RE = re.compile(r"""Volume\.(?:from_name\(\s*["']([^"']+)|\(name\s*=\s*["']([^"']+))|Volume\(\s*name\s*=\s*["']([^"']+)""")
REPO_RE = re.compile(r"""repo_id\s*=\s*["']([^"']+)["']""")
PROVIDER_OF = (("worker_modal_", "modal"), ("worker_beam_", "beam"))  # flash has no seedable volumes


def sh(*cmd: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(WORKDIR))


def sh_live(*cmd: str, timeout: int = 3600) -> tuple[int, str]:
    """Run cmd forwarding output live; returns (returncode, tail). For long uploads."""
    import time

    out: list[str] = []
    last_beat = time.monotonic()
    try:
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, cwd=str(WORKDIR)) as p:
            assert p.stdout is not None
            for line in p.stdout:
                now = time.monotonic()
                if line.lstrip().startswith("[beam://"):
                    if now - last_beat >= 60:  # progress redraws -> heartbeat only
                        print("  | ...still uploading...", flush=True)
                        last_beat = now
                    continue
                print("  | " + line.rstrip(), flush=True)
                out.append(line)
            rc = p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"  | TIMEOUT after {timeout}s -> killing")
        assert p.stdout is not None
        p.kill()
        p.wait()
        return 124, f"timed out after {timeout}s"
    return rc, "".join(out[-20:])


def volume_prefix(provider: str, volume: str) -> str:
    """HF cache layout is $HF_HOME/hub/models--*, so slugs live under hub/ when it exists."""
    root = sh("modal", "volume", "ls", volume) if provider == "modal" else sh("beam", "ls", volume)
    if root.returncode == 0 and "hub" in root.stdout:
        return "hub/"
    return ""


def remote_present(provider: str, volume: str, path: str) -> bool:
    r = sh("modal", "volume", "ls", volume, path) if provider == "modal" \
        else sh("beam", "ls", f"{volume}/{path}")
    combined = (r.stdout or "") + (r.stderr or "")
    if "No such file" in combined or "0 items" in combined:
        return False
    if r.returncode != 0 or not combined.strip():
        return False
    if Path(path).name.startswith("models--"):
        # partial uploads (e.g. killed beam cp) must not pass as present
        return all(d in combined for d in ("blobs", "refs", "snapshots"))
    return True


def die(msg: str, tmp: Path | None = None) -> "NoReturn":
    if tmp is not None:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"FAILED {msg} -> bailing")
    raise SystemExit(1)


def shared_repos(family: str, directory: Path) -> set[str]:
    repos: set[str] = set()
    for f in sorted(directory.glob("_shared_*.py")):
        try:
            m = importlib.import_module(f"workers.{family}.{f.stem}")
        except Exception as e:
            print(f"WARN import {f.stem}: {e}")
            continue
        repos.update(v for k, v in vars(m).items() if isinstance(v, str)
                     and (k.endswith(("_REPO", "_ID")) or k == "MODEL_ID") and "/" in v and " " not in v)
    return repos


class Inaccessible(Exception):
    pass


# Full-repo snapshots are banned for buffets: only the files workers resolve.
ALLOW_PATTERNS = {
    "Comfy-Org/MiniMax-H3": [
        "diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors",
        "text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors",
    ],
}


def fetch(repo: str, tmp: Path, patterns: list[str] | None = None) -> None:
    from huggingface_hub import snapshot_download

    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        snapshot_download(repo_id=repo, cache_dir=str(tmp), allow_patterns=patterns)


def budget_for(size: int | None) -> int:
    return max(1800, (size or 0) // 5_000_000)  # >=5MB/s assumed, 30min floor


def repo_size(repo: str, patterns: list[str] | None = None) -> int | None:
    try:
        import fnmatch

        from huggingface_hub import HfApi
        from huggingface_hub.utils import HfHubHTTPError

        try:
            info = HfApi().model_info(repo, files_metadata=True)
        except HfHubHTTPError as e:
            if e.response is not None and e.response.status_code in (401, 403, 404):
                raise Inaccessible(f"HTTP {e.response.status_code}") from e
            raise
        siblings = info.siblings or []
        if patterns:
            siblings = [s for s in siblings if any(fnmatch.fnmatch(s.rfilename, p) for p in patterns)]
        total = sum(s.size or 0 for s in siblings)
        return total or None
    except Inaccessible:
        raise
    except Exception as e:
        print(f"WARN size lookup {repo}: {e}")
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="all", choices=["modal", "beam", "all"])
    ap.add_argument("--only", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    only = {s for s in args.only.split(",") if s} or None

    # Reap staging dirs from killed runs (SIGKILL skips finally); only one seed runs at a time.
    for stale in Path(tempfile.gettempdir()).glob("seed-*"):
        if stale.is_dir():
            print(f"reaping stale staging dir {stale}")
            shutil.rmtree(stale, ignore_errors=True)

    plan: dict[tuple[str, str], set[str]] = {}
    for wf in sorted((WORKDIR / "workers").glob("*/worker_*.py")):
        if wf.parent.name == "voice" or (only and wf.parent.name not in only and wf.stem not in only):
            continue
        provider = next((p for tag, p in PROVIDER_OF if tag in wf.name), None)
        if provider is None or (args.provider != "all" and provider != args.provider):
            continue
        text = wf.read_text()
        vols = {m.group(1) or m.group(2) or m.group(3) for m in VOL_RE.finditer(text)}
        repos = shared_repos(wf.parent.name, wf.parent) | set(REPO_RE.findall(text))
        print(f"{wf.relative_to(WORKDIR)} -> volumes={sorted(vols)} repos={sorted(repos)}")
        for v in vols:
            plan.setdefault((provider, v), set()).update(repos)

    prefixes = {(p, v): volume_prefix(p, v) for p, v in sorted(plan)}
    up = skip = blocked = 0
    for (provider, volume), repos in sorted(plan.items()):
        prefix = prefixes[(provider, volume)]
        pending: list[tuple[str, int | None, str, str]] = []
        for repo in sorted(repos):
            slug = "models--" + repo.replace("/", "--")
            path = prefix + slug
            if remote_present(provider, volume, path):
                print(f"{provider}/{volume} {repo}: already-there")
                continue
            try:
                size = repo_size(repo, ALLOW_PATTERNS.get(repo))
            except Inaccessible as e:
                print(f"{provider}/{volume} {repo}: inaccessible ({e}), skipping - check worker ref or HF token")
                blocked += 1
                continue
            pending.append((repo, size, slug, path))
        pending.sort(key=lambda t: (t[1] is None, t[1] or 0))  # smallest first, unknown last
        free = shutil.disk_usage(tempfile.gettempdir()).free
        for repo, size, slug, path in pending:
            need = f"{size // 1_000_000_000}G" if size else "unknown-size"
            if args.dry_run:
                budget = budget_for(size)
                if size and size > free:
                    print(f"{provider}/{volume} {repo}: would-skip no-space (need {need}, free {free // 1_000_000_000}G)")
                else:
                    print(f"{provider}/{volume} {repo}: would-upload ({need}, budget {budget // 60}min)")
                continue
            if size and size > free:
                print(f"{provider}/{volume} {repo}: no-space, skipping (need {need}, free {free // 1_000_000_000}G)")
                skip += 1
                continue
            budget = budget_for(size)
            tmp = Path(tempfile.mkdtemp(prefix="seed-"))
            print(f"{provider}/{volume} {repo}: downloading ({need}, budget {budget // 60}min) -> {tmp}", flush=True)
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                    fut = ex.submit(fetch, repo, tmp, ALLOW_PATTERNS.get(repo))
                    try:
                        fut.result(timeout=budget)
                    except concurrent.futures.TimeoutError:
                        die(f"{provider}/{volume} {repo}: download hung (no return in {budget // 60}min)", tmp)
                src = tmp / slug
                dest = f"/{path}" if provider == "modal" else f"beam://{volume}/{path}"
                print(f"{provider}/{volume} {repo}: uploading -> {dest}", flush=True)
                if provider == "modal":
                    res = sh("modal", "volume", "put", volume, str(src), dest, timeout=3600)
                    rc, tail = res.returncode, (res.stderr or res.stdout or "").strip()[-500:]
                else:
                    rc, tail = sh_live("beam", "cp", str(src), dest, timeout=3600)
                if rc != 0:
                    die(f"{provider}/{volume} {repo}: upload {tail.strip()[:300]}", tmp)
                print(f"{provider}/{volume} {repo}: uploaded")
                up += 1
            except SystemExit:
                raise
            except Exception as e:
                die(f"{provider}/{volume} {repo}: {e}", tmp)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
    print(f"ALL DONE uploaded={up} skipped={skip} blocked={blocked}")
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
