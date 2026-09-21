"""Run all 4 Modal core verifications in parallel, bail on error, report every 30s."""
from __future__ import annotations

import base64
import io
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import modal
import requests
from PIL import Image, ImageDraw, ImageFont

WORKDIR = Path("/Users/gyorgygutai/Projects/personal-infra/inference-tooling")
ARTIFACTS = WORKDIR / "workers" / "verification" / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

START_ISO = datetime.now(timezone.utc).isoformat()
START_TS = datetime.now().strftime("%Y%m%d_%H%M%S")

RESULTS: dict = {}
ERRORS: dict = {}
LOCK = threading.Lock()

def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def make_test_png_base64(size=(64, 64)) -> str:
    img = Image.new("RGB", size, color=(255, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle([16, 16, 48, 48], fill=(0, 255, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def poll_logs(app_name: str, stop_event: threading.Event):
    """Poll modal app logs every 10s until stop_event is set."""
    import subprocess
    while not stop_event.is_set():
        try:
            result = subprocess.run(
                ["modal", "app", "logs", app_name, "--since", START_ISO,
                 "--timestamps", "--tail", "50"],
                capture_output=True, text=True, timeout=30,
                cwd=str(WORKDIR),
            )
            lines = result.stdout.strip().splitlines()
            if lines:
                tail = "\n".join(lines[-10:])
                with LOCK:
                    print(f"\n--- {app_name} logs ---\n{tail}\n--- end ---\n", flush=True)
        except Exception as e:
            pass
        stop_event.wait(timeout=10)


def download_artifact(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        dest.write_bytes(r.content)
        return True
    except Exception as e:
        log(f"  FAIL download {url}: {e}")
        return False


def run_tinysd():
    app_name = "tiny-sd-worker"
    cls_name = "TinySDWorker"
    method = "generate"
    good = {"prompt": "a red square", "seed": 7}
    try:
        log(f"[tinysd] spawning {method}")
        Cls = modal.Cls.from_name(app_name, cls_name)
        call = getattr(Cls(), method).spawn(**good)
        log(f"[tinysd] waiting for result (call id={call.object_id})")
        out = call.get(timeout=300)
        log(f"[tinysd] got result: {out}")
        url = out["artifact"]["presigned_url"]
        dest = ARTIFACTS / f"tinysd_{START_TS}.png"
        if download_artifact(url, dest):
            with LOCK:
                RESULTS["tinysd"] = str(dest)
            log(f"[tinysd] saved to {dest}")
        else:
            raise RuntimeError("artifact download failed")
    except Exception as e:
        with LOCK:
            ERRORS["tinysd"] = str(e)
        log(f"[tinysd] ERROR: {e}")


def run_vision():
    app_name = "small-vision-worker"
    cls_name = "SmallVisionWorker"
    method = "analyze"
    test_b64 = make_test_png_base64()
    good = {"image_base64": test_b64}
    try:
        log(f"[vision] spawning {method}")
        Cls = modal.Cls.from_name(app_name, cls_name)
        call = getattr(Cls(), method).spawn(**good)
        log(f"[vision] waiting for result (call id={call.object_id})")
        out = call.get(timeout=300)
        log(f"[vision] got result: {out}")
        dest = ARTIFACTS / f"vision_{START_TS}.json"
        dest.write_text(json.dumps(out, indent=2))
        with LOCK:
            RESULTS["vision"] = str(dest)
        log(f"[vision] saved to {dest}")
    except Exception as e:
        with LOCK:
            ERRORS["vision"] = str(e)
        log(f"[vision] ERROR: {e}")


def run_flux():
    app_name = "flux2-klein9b-worker"
    cls_name = "FluxKleinWorker"
    method = "generate"
    good = {"prompt": "a red square", "seed": 7}
    try:
        log(f"[flux2] spawning {method}")
        Cls = modal.Cls.from_name(app_name, cls_name)
        call = getattr(Cls(), method).spawn(**good)
        log(f"[flux2] waiting for result (call id={call.object_id})")
        out = call.get(timeout=300)
        log(f"[flux2] got result: {out}")
        url = out["artifact"]["presigned_url"]
        dest = ARTIFACTS / f"flux2_{START_TS}.png"
        if download_artifact(url, dest):
            with LOCK:
                RESULTS["flux2"] = str(dest)
            log(f"[flux2] saved to {dest}")
        else:
            raise RuntimeError("artifact download failed")
    except Exception as e:
        with LOCK:
            ERRORS["flux2"] = str(e)
        log(f"[flux2] ERROR: {e}")


def run_krea():
    app_name = "krea2-ref2img-worker"
    cls_name = "Krea2Ref2ImgWorker"
    method = "generate"
    good = {"prompt": "a red square", "seed": 7}
    try:
        log(f"[krea2] spawning {method}")
        Cls = modal.Cls.from_name(app_name, cls_name)
        call = getattr(Cls(), method).spawn(**good)
        log(f"[krea2] waiting for result (call id={call.object_id})")
        out = call.get(timeout=300)
        log(f"[krea2] got result: {out}")
        url = out["artifact"]["presigned_url"]
        dest = ARTIFACTS / f"krea2_{START_TS}.png"
        if download_artifact(url, dest):
            with LOCK:
                RESULTS["krea2"] = str(dest)
            log(f"[krea2] saved to {dest}")
        else:
            raise RuntimeError("artifact download failed")
    except Exception as e:
        with LOCK:
            ERRORS["krea2"] = str(e)
        log(f"[krea2] ERROR: {e}")


def main():
    log("=== Starting Modal core verification ===")
    log(f"Start ISO: {START_ISO}")
    log(f"Artifacts dir: {ARTIFACTS}")

    threads = []
    for fn in [run_tinysd, run_vision, run_flux, run_krea]:
        t = threading.Thread(target=fn, daemon=True)
        t.start()
        threads.append(t)

    # Start log pollers
    log_stop = threading.Event()
    pollers = []
    for app_name in ["tiny-sd-worker", "small-vision-worker", "flux2-klein9b-worker", "krea2-ref2img-worker"]:
        p = threading.Thread(target=poll_logs, args=(app_name, log_stop), daemon=True)
        p.start()
        pollers.append(p)

    # Wait for all worker threads
    for t in threads:
        t.join()

    # Stop log pollers
    log_stop.set()
    for p in pollers:
        p.join(timeout=5)

    log("=== Results ===")
    for name, path in RESULTS.items():
        log(f"  OK   {name}: {path}")
    for name, err in ERRORS.items():
        log(f"  FAIL {name}: {err}")

    if ERRORS:
        log("=== BAIL: one or more workers failed ===")
        sys.exit(1)
    else:
        log("=== ALL PASSED ===")
        sys.exit(0)


if __name__ == "__main__":
    main()
