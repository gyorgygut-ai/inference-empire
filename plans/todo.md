# Execution tiers per group

Conventions (all groups): every worker file exposes module-level
`generate(...)` (validate input OUTSIDE the `try` so `ValidationError`
propagates unwrapped, delegate to `do_inference` inside, return output
contract; inference failures re-raise as `RuntimeError(...) from e`;
h3/comfy shapes vary but follow the same pattern). Provider decoration stays
purely deploy-surface:
beam's decorated entry is renamed (`dispatch`), flash/modal classes delegate
one line to module `generate`. Test shape is setup / blank / act / blank /
assert, one assert per test (`bucket.fetch(key) == canned_bytes` — a missing
key raises, so presence + exactness in a single shot). Unit tests take
`(bucket)` and call module `generate` directly with fakes — no mocks at all.
Invalid-input tests expect `pydantic.ValidationError` (unit + deployed twin
each). E2E tests take `(e2e_target, bucket)`; the target receives
`(worker_mod, inputs, deps, storage)` — local rung patches
`load_dependencies` (proving the seam) then drives module `generate`
(`run_async` additionally polls via `FakeAsyncRunner`); deployed rung is
module-scoped `deployed_worker` (setup deploys that file's worker, native
invoke per provider, teardown undeploys; ignores deps/storage). Markers:
`-m local_e2e` / `-m deployed_e2e`. Gates per group: every test ≤~25 lines,
`ruff` clean.

## Group 0 — Harness + services

- [x] 0.1 restructuring: 3-file service map, new `runner.py` interface, new `inference/` fakes, `platform/` prefix drops, rewire imports
- [x] 0.2 cleanup: pytest config + markers, `workers/conftest.py`, `workers/e2e_targets.py`, hygiene
- [x] 0.3 unit tests: n/a (no worker code yet)
- [x] 0.4 local e2e tests: n/a
- [x] 0.5 deployed e2e tests: n/a
- [x] 0.6 clean up 2: `rg` sweep for leftover `Real*`/`_calls`/`real_*`, line-count gate
- [x] 0.7 verify: `pytest --collect-only` clean, imports resolve
- [x] 0.8 verify: local e2e n/a
- [x] 0.9 verify: deployed e2e n/a

## Group 1 — Flux2 (pilot)

- [x] 1.1 restructuring: shared rename, `ensure_dotenv()` into `_shared`
- [x] 1.2 cleanup: dead `START`/`START_TIME`, broken modal `main()`, beam `load_deps` wrapper, `generate_web` delegates, flash dep pins
- [x] 1.3 unit tests: 3 files, one assert each
- [x] 1.4 local e2e tests: 3 files, `-m local_e2e`
- [ ] 1.5 deployed e2e tests: `deployed_worker` (setup deploys per file, native invoke, teardown undeploys), `-m deployed_e2e`, incl. invalid-reject case
- [x] 1.6 clean up 2: contract parity, negative check, nits
- [x] 1.7 verify: `pytest workers/flux2 -m "not deployed_e2e"` green
- [x] 1.8 verify: `-m local_e2e workers/flux2` green
- [ ] 1.9 verify: `-m deployed_e2e workers/flux2` green (via `deployed_worker`)

## Group 2 — Krea2

- [x] 2.1 restructuring: shared rename, beam `**kwargs` signature fix
- [x] 2.2 cleanup: dotenv helper, modal delegate, `_download_models` delete-if-unwired, flash dep pins
- [x] 2.3 unit tests: 3 files, one assert each
- [x] 2.4 local e2e tests: 3 files, `-m local_e2e` (`run`/`run_async`)
- [ ] 2.5 deployed e2e tests: `deployed_worker` (setup deploys per file, native invoke, teardown undeploys), `-m deployed_e2e`, incl. invalid-reject case
- [x] 2.6 clean up 2: contract parity, negative check, nits
- [x] 2.7 verify: `pytest workers/krea2 -v` green
- [x] 2.8 verify: `-m local_e2e workers/krea2` green
- [ ] 2.9 verify: `-m deployed_e2e workers/krea2` green (via `deployed_worker`)

## Group 3 — Vision

- [x] 3.1 restructuring: shared `run_analyze` → `do_inference`
- [x] 3.2 cleanup: drop `require_storage` + `self.storage` ×3, modal `_do_inference`, delegate, dep pins
- [x] 3.3 unit tests: 3 files, assert output equals canned (artifact N/A, commented)
- [x] 3.4 local e2e tests: 3 files, `-m local_e2e`
- [ ] 3.5 deployed e2e tests: `deployed_worker` (setup deploys per file, native invoke, teardown undeploys), `-m deployed_e2e`, incl. invalid-reject case (+ storage-shape pin)
- [x] 3.6 clean up 2: contract parity, negative check, nits
- [x] 3.7 verify: `pytest workers/vision -v` green
- [x] 3.8 verify: `-m local_e2e workers/vision` green
- [ ] 3.9 verify: `-m deployed_e2e workers/vision` green (via `deployed_worker`)

## Group 4 — H3 (3 commits)

- [x] 4.1 restructuring: non-comfy rename, `apply_torch_shims()`, comfy `do_inference` extraction
- [x] 4.2 cleanup: dead `START_TIME` ×2, flash try/except, modal delegates, ref2va input-type reconcile, ruff nits
- [x] 4.3 unit tests: 6 non-comfy + 3 comfy files, one assert each
- [x] 4.4 local e2e tests: 9 files, `-m local_e2e`
- [ ] 4.5 deployed e2e tests: `deployed_worker` (setup deploys per file, native invoke, teardown undeploys), `-m deployed_e2e`, incl. invalid-reject case
- [x] 4.6 clean up 2: contract parity, negative check, nits
- [x] 4.7 verify: `pytest workers/h3 -v` green
- [x] 4.8 verify: `-m local_e2e workers/h3` green
- [ ] 4.9 verify: `-m deployed_e2e workers/h3` green (via `deployed_worker`)

## Group 5 — Voice

- [x] 5.1 restructuring: `_shared_voice_chat.py` extracted
- [x] 5.2 cleanup: worker imports from shared, no duplicates
- [x] 5.3 unit tests: pure-helper tests, mock-free, one assert each
- [x] 5.4 local e2e tests: modal voice only, `-m local_e2e` (beam parked)
- [ ] 5.5 deployed e2e tests: modal voice only via `deployed_worker` (modal `spawn` + `.result()`, undeploy in teardown), incl. invalid-reject case (beam parked until vendor-vs-delete)
- [x] 5.6 clean up 2: nits, `ruff`
- [x] 5.7 verify: `pytest workers/voice -v` green
- [x] 5.8 verify: `-m local_e2e workers/voice` green
- [ ] 5.9 verify: `-m deployed_e2e workers/voice` green (via `deployed_worker`)

## Error handling hardening (done, all groups)

- [x] `from e` on all 19 `raise RuntimeError(f"inference failed: {e}")` wrappers (flux2×3, krea2×3, vision×3, h3×9, voice×1)
- [x] Input validation moved outside `try` in all 19 `generate` functions; 16 invalid-input tests expect `pydantic.ValidationError`
- [x] Torch `load_library` shim re-raises `OSError` with path (`_shared_minimax_h3_fl2va.py`, `_shared_minimax_h3_ref2va.py`)
- [x] Comfy poll `except-pass` narrowed to `(ConnectionError, Timeout, ValueError)` with logged retry count (`_shared_minimax_h3_ref2va_comfy.py`)
- [x] Re-verify: 61 passed (`-m "not deployed_e2e"`), 20 passed (`-m local_e2e`), `ruff check workers/` clean
