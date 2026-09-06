# Dep Parity — pre-flight, not e2e

## Goal
Fail in seconds locally on env drift instead of hours in cloud.
Separate concern from e2e; runs before it.

## Rule
Worker file is the single source of truth. No second requirements file.

## New
- `workers/services/deps/dep_check.py` (~20 lines): `extract_pins(worker_path)`
  via AST (no import, no SDK), `check_installed(pins)` via `importlib.metadata`,
  raises exact mismatch. Also `python==3.11`, `ffmpeg` on PATH, torch shim.

## Harden
- Pin bare names (`safetensors==x`, `huggingface_hub==x`), narrow ranges to `==`.
- Krea2 vs Flux2 split enforced per-worker.
