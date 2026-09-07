# Plan: Unit Tests + tiny_sd E2E Parallel Runs

## Precondition (done)

All flash e2e tests marked skipped via module-level
`pytestmark = pytest.mark.skip(reason="flash e2e written but skipped")`.
Verified: 16 skipped across 8 files (flux2, tiny_sd, krea2, vision, h3 x4).
Files touched:
- `workers/flux2/tests/test_e2e_worker_flash_cls_flux2_klein9b.py`
- `workers/tiny_sd/tests/test_e2e_worker_flash_cls_tiny_sd.py`
- `workers/krea2/tests/test_e2e_worker_flash_cls_krea2_ref2img.py`
- `workers/vision/tests/test_e2e_worker_flash_cls_small_vision.py`
(h3 x4 already had module-level skip; untouched.)

## Todo 1: Run all unit tests

- Command: `.venv/bin/python -m pytest workers/ -k "not e2e"` (repo `python` is 2.7; use `.venv/bin/python`)
- Expect: 257 passed (per `workers/VERIFICATION.md`).
- If succeeds: proceed to Todo 2.
- If fails: stop, report output, discuss with owner. Do not proceed.

## Todo 2: Start the 2 tiny_sd e2e tests SEPARATELY, in parallel, with live log commentary

- Test A (Beam): `workers/tiny_sd/tests/test_e2e_worker_beam_tq_tiny_sd.py`
  hits live Beam deployment via `dispatch.put(**GOOD)`; poll with
  `beam logs --task-id <id> --timeout 3600 --follow`, commentate `[INIT] -> [REQ] -> [GEN] -> [R2] -> [OK]/[ERR]`.
- Test B (Modal): `workers/tiny_sd/tests/test_e2e_worker_modal_cls_tiny_sd.py`
  hits live Modal app `tiny-sd-worker/TinySDWorker.spawn(**GOOD)`; follow with
  `modal app logs <app-name>`, commentate same tag order.
- Run A and B as two separate parallel processes (not a single pytest invocation),
  stream and commentate both logs live to the owner.
- Flash tiny_sd e2e excluded (skipped, flash dev not available).
- Requires: live Beam + Modal deployments, creds, network. Owner-operated.
- If either fails: stop, report, discuss. Do not retry without owner go-ahead.

## Status

Parked. Awaiting further owner instructions before starting Todo 1.
