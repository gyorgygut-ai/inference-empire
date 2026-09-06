# Phase 4 — H3 (largest phase — 3 commits)

Files: 4 shared (`_shared_minimax_h3_{fl2va,ref2va,comfy,ref2va_comfy}.py`),
9 workers + 9 test files. Suggest 3 commits: non-comfy, comfy, tests.
Same stupid-simple shape everywhere: setup / blank / act / blank / assert.

## 1. Tests first (RED)

- `workers/h3/tests/__init__.py` (empty)
- Non-comfy, one assert each (the bucket has exactly the canned video bytes):
  `test_worker_{beam_tq,flash_cls,modal_cls}_minimax_h3_{fl2va,ref2va}.py`
  (6 files). `monkeypatch` `load_dependencies` → `(FakeVideoPipe(frames,
  audio), FakeWriteVideoAudio(canned_video_bytes))` — both source fakes take
  their canned payload in the ctor (required). Assert
  `bucket.fetch(key_of(out)) == canned_video_bytes`.
- Comfy (mock at transport level — the only place beyond the
  `load_dependencies` seam, since there is no pipe object to fake), one assert
  on served bytes:
  - `test_worker_beam_tq_minimax_h3_ref2va_comfy.py`: `monkeypatch`
    `requests` in the worker namespace — canned `prompt_id`, history with
    `save.videos[0]`, video bytes on view URL.
  - `test_worker_flash_cls_minimax_h3_comfy.py` +
    `test_worker_flash_pre_minimax_h3_ref2va_comfy.py`: stub endpoint object
    with canned `runsync` job (`error=None`, `output={"images": [...]}`).

## 1b. E2E tests (same bodies, `e2e_target` + `bucket`)

9 files mirroring the unit files (`test_e2e_*`), `run` for flash/modal sync
paths, `run_async` for `tq`. Marked `@pytest.mark.local_e2e` /
`@pytest.mark.deployed_e2e`. One assert each.

## 2. Shared cleanup

- `run_generate` → `do_inference` in `_shared_minimax_h3_fl2va.py:114` and
  `_shared_minimax_h3_ref2va.py:276`. Signatures unchanged:
  `(pipe, write_video_audio, storage: Storage, req)`.
- New `apply_torch_shims()` helper per non-comfy shared file: the
  dist-shim + `torch.ops.load_library` patch block is triplicated across
  modal `load()`s and flash comfy `__init__`s. One home in shared; workers
  call one line. (Flux2 already keeps its shim inside shared
  `load_pipeline` — same pattern.)
- Comfy shared: extract the submit/poll/fetch flow so comfy workers also get
  `do_inference`:
  - Beam: `do_inference(comfy_base_url, storage, req)` — submit + 600s poll
    + fetch + `upload_result` (moves L93–122 out of
    `worker_beam_tq_minimax_h3_ref2va_comfy.py`).
  - Flash: `run_comfy_endpoint(endpoint, payload)` helper (the `asyncio.run`
    + ThreadPool fallback, L63–77, identical in both flash comfy workers) +
    `do_inference(endpoint, storage, req)`.

## 3. Worker cleanup

- Delete dead `START_TIME` (both beam_tq non-comfy, L18).
- Standardize error handling: flash `generate()` (ref2va/fl2va) has **no
  try/except** — raw errors escape. Add the `try/except → RuntimeError(...) from e`
  wrapper matching beam/modal (validation stays outside the `try`).
  Small behavior change, flagged.
- Modal `generate_web` ×2 → delegate to `generate` (fl2va's copy duplicates
  the call without even try/except).
- `worker_modal_cls_minimax_h3_ref2va.py`: reconcile the double input types
  (`MiniMaxH3Ref2VAInput` + `ValidatedRef2VAInput` both imported) — check the
  shared distinction at execution; `generate_web` should most likely take
  the validated type directly.
- Fix import-order nit (blank-line-separated `require_storage` import in
  beam/modal files) via ruff.
- All non-comfy workers: import/call swap to `do_inference`.

## 4. Verify

- `pytest workers/h3 -v` green. Negative check + output-model keys ⊆
  `contracts/*.json`.
- `-m local_e2e workers/h3` green; then deploy test env, `-m deployed_e2e
  workers/h3` green, undeploy.
- `rg "run_generate" workers/h3` → zero hits.
- `ruff check` clean. No test over ~25 lines.

## 5. Commits (3)

1. `refactor(workers): lean h3 non-comfy workers on do_inference`
2. `refactor(workers): extract comfy do_inference in h3 shared`
3. `test(workers): add h3 unit + e2e tests per worker file`
