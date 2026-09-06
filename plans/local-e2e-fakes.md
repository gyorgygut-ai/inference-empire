# Local E2E Fakes — 3 dict fakes, local runners, wiring

## Goal
Default `pytest workers/ --target fake` runs every worker against a local
fake of its own provider. Cloud stays on the existing `deployed_e2e` marker,
owner-only.

## Non-goals
- No Docker. No HTTP, no ports, no processes. In-process dicts.
- No new env vars, no new flags.
- No canned outputs in the e2e path (canned stays in fast unit tests).
- No edits to `workers/*/worker_*.py`, `workers/*/_shared_*.py`, `contracts/*.json`.

## New — fake servers (~10 lines each, zero shared state)
- `workers/mock_server/flash/fake.py` — `submit(inputs) -> id`, `result(id)`
  runs `worker_mod.generate(storage, *tiny_deps, **inputs)`.
- `workers/mock_server/beam/fake.py` — same, Beam id/status names.
- `workers/mock_server/modal/fake.py` — same, Modal id/status names.
- One dict per fake module, fresh per session. No shared state.

```python
JOBS = {}
def submit(worker_mod, storage, deps, inputs):
    tid = f"task-{len(JOBS)}"
    JOBS[tid] = (worker_mod, storage, deps, inputs)
    return tid
def result(tid):
    worker_mod, storage, deps, inputs = JOBS.pop(tid)
    return worker_mod.generate(storage, *deps, **inputs)
```

## New — local services (real code untouched, no ifs)
- `workers/services/platform/flash_platform_local.py` — `deploy()` fresh dict
  session, `undeploy()` clears only it. Same for beam/modal.
- `workers/services/runner/runner_local.py` — `LocalFlash/Beam/ModalRunner`:
  `submit/poll/result/run`, thin wrappers over own fake dict.

## Wiring (two files only)
- `workers/conftest.py:22-36` — default (no marker) builds local path via the
  `load_dependencies` seam (`workers/e2e_targets.py:40-42`); marker path unchanged.
- `workers/e2e_targets.py:88-117` — cloud untouched, local never calls it.

## Acceptance
- Invalid rejects; good returns contract; artifact fetchable; dict empty after suite.

## Verify
- `python -m pytest workers/vision/tests/ --target fake -x -q`
- `python -m pytest workers/ --target fake -q`
