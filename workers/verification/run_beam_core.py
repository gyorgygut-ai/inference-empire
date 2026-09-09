"""Run all 4 Beam core verifications in parallel, bail on error/stuck, report live.

Mirrors run_modal_core.py but uses Beam task_queue dispatch. Beam's
task.result(wait=True) blocks on SSE with no timeout, so each worker thread
polls task.status() every 10s with a hard deadline (STUCK_AFTER_S). On
deadline the task is stopped via `beam task stop` and recorded as stuck.
"""
from __future__ import annotations

import base64
import io
import json
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import requests
from PIL import Image

WORKDIR = Path("/Users/gyorgygutai/Projects/personal-infra/inference-tooling")
sys.path.insert(0, str(WORKDIR))
ARTIFACTS = WORKDIR / "workers" / "verification" / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

START_TS = datetime.now().strftime("%Y%m%d_%H%M%S")

# Hard deadline per worker: cold start + inference must finish within this.
DEADLINE_S = 600
POLL_S = 10

RESULTS: dict = {}
ERRORS: dict = {}
TASK_IDS: dict = {}
LOCK = threading.Lock()


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def make_test_png_base64(size=(8, 8)) -> str:
    img = Image.new("RGB", size, color=(0, 255, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def stop_task(task_id: str):
    try:
        subprocess.run(
            ["beam", "task", "stop", task_id],
            capture_output=True, text=True, timeout=30,
            cwd=str(WORKDIR),
        )
    except Exception:
        pass


def download_artifact(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        dest.write_bytes(r.content)
        return True
    except Exception as e:
        log(f"  FAIL download {url}: {e}")
        return False


def wait_for_task(name: str, task, good: dict):
    """Poll task.status() until terminal or deadline. Returns result dict or raises."""
    task_id = task.id
    with LOCK:
        TASK_IDS[name] = task_id
    log(f"[{name}] enqueued task {task_id[:8]}... waiting (deadline {DEADLINE_S}s)")
    start = time.time()
    last_status = None
    while True:
        elapsed = time.time() - start
        if elapsed > DEADLINE_S:
            log(f"[{name}] STUCK: no terminal state after {int(elapsed)}s, stopping task")
            stop_task(task_id)
            raise TimeoutError(f"stuck: task {task_id[:8]} not complete after {int(elapsed)}s")
        try:
            status = str(task.status())
        except Exception as e:
            raise RuntimeError(f"status poll failed: {e}")
        if status != last_status:
            log(f"[{name}] status={status} after {int(elapsed)}s")
            last_status = status
        if status in ("COMPLETE",):
            out = task.result()
            if out is None:
                raise RuntimeError("beam task returned None - check beam logs")
            return out
        if status in ("ERROR", "TIMEOUT", "CANCELLED"):
            raise RuntimeError(f"task ended with status={status} - check beam logs")
        time.sleep(POLL_S)


def run_worker(name: str, module: str, good: dict, dest_name: str, is_json: bool):
    try:
        worker_mod = __import__(module, fromlist=["dispatch"])
        task = worker_mod.dispatch.put(**good)
        if task is False or task is None:
            raise RuntimeError("dispatch.put failed to enqueue")
        out = wait_for_task(name, task, good)
        log(f"[{name}] got result keys: {list(out.keys()) if isinstance(out, dict) else type(out)}")
        if is_json:
            dest = ARTIFACTS / f"{dest_name}_{START_TS}.json"
            dest.write_text(json.dumps(out, indent=2))
        else:
            url = out["artifact"]["presigned_url"]
            dest = ARTIFACTS / f"{dest_name}_{START_TS}.png"
            if not download_artifact(url, dest):
                raise RuntimeError("artifact download failed")
        with LOCK:
            RESULTS[name] = str(dest)
        log(f"[{name}] saved to {dest}")
    except Exception as e:
        with LOCK:
            ERRORS[name] = str(e)
        log(f"[{name}] ERROR: {e}")


def run_tinysd():
    run_worker("tinysd", "workers.tiny_sd.worker_beam_tq_tiny_sd",
               {"prompt": "a red square", "seed": 7}, "beam_tinysd", False)


def run_vision():
    run_worker("vision", "workers.vision.worker_beam_tq_small_vision",
               {"image_base64": make_test_png_base64()}, "beam_vision", True)


def run_flux():
    run_worker("flux2", "workers.flux2.worker_beam_tq_flux2_klein9b",
               {"prompt": "a red square", "seed": 7}, "beam_flux2", False)


def run_krea():
    run_worker("krea2", "workers.krea2.worker_beam_tq_krea2_ref2img",
               {"prompt": "a red square", "seed": 7}, "beam_krea2", False)


def main():
    log("=== Starting Beam core verification ===")
    log(f"Artifacts dir: {ARTIFACTS}")

    threads = []
    for fn in [run_tinysd, run_vision, run_flux, run_krea]:
        t = threading.Thread(target=fn, daemon=True)
        t.start()
        threads.append(t)

    # 30s heartbeat until all worker threads finish
    while any(t.is_alive() for t in threads):
        time.sleep(30)
        with LOCK:
            done = list(RESULTS.keys())
            failed = list(ERRORS.keys())
        log(f"--- heartbeat: OK={done} FAIL={failed} tasks={TASK_IDS}")

    for t in threads:
        t.join()

    log("=== Results ===")
    for worker_name, path in RESULTS.items():
        log(f"  OK   {worker_name}: {path}")
    for worker_name, err in ERRORS.items():
        log(f"  FAIL {worker_name}: {err}")

    if ERRORS:
        log("=== BAIL: one or more workers failed/stuck ===")
        sys.exit(1)
    else:
        log("=== ALL PASSED ===")
        sys.exit(0)


if __name__ == "__main__":
    main()
