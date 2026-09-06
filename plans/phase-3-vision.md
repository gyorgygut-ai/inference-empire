# Phase 3 — Vision

Files: `workers/vision/_shared_small_vision.py`,
`worker_{beam_eq,flash_cls,modal_cls}_small_vision.py` + 3 test files.

Same TDD order: tests first (RED), then rename + cleanup (GREEN).
Same stupid-simple shape: setup / blank / act / blank / assert.

## 1. Tests first (RED)

- `workers/vision/tests/__init__.py` (empty)
- `workers/vision/tests/test_worker_beam_eq_small_vision.py`
- `workers/vision/tests/test_worker_flash_cls_small_vision.py`
- `workers/vision/tests/test_worker_modal_cls_small_vision.py`

Template (one assert): `monkeypatch` `load_dependencies` → `(FakeVisionModel(canned),
FakeVisionProcessor(canned), "fake-prompt")` — source fakes take the canned
result dict in the ctor (required). Drive `analyze`, assert the returned
output **equals the canned result**. Artifact case marked N/A with comment
(vision returns JSON — the "(if applicable)" qualifier). Invalid input →
`pydantic.ValidationError` (own one-assert test). Real PIL decode path kept (inline 8×8
PNG as the request image — that is request setup, not fake prep).

## 1b. E2E tests (same bodies, `e2e_target` + `bucket`)

- `workers/vision/tests/test_e2e_worker_beam_eq_small_vision.py` (`run` — `eq` direct response)
- `workers/vision/tests/test_e2e_worker_flash_cls_small_vision.py` (`run`)
- `workers/vision/tests/test_e2e_worker_modal_cls_small_vision.py` (`run_async`)

Marked `@pytest.mark.local_e2e` / `@pytest.mark.deployed_e2e`. One assert each.

## 2. Shared cleanup (`_shared_small_vision.py`)

- L94: `def run_analyze(` → `def do_inference(`. Signature unchanged:
  `(model, processor, analyze_prompt: str, req: SmallVisionInput)`.
- Nothing else — shared is already lean.

## 3. Worker cleanup — the storage bug

Vision returns JSON; storage is never used. Yet all 3 workers call
`require_storage`, which **raises when storage is None and no R2 env exists**
(`r2_storage.py:45-54`, moved from `real_r2.py` in Phase 0). Live vision
without R2 configured is broken today.

- All 3 workers: drop the `require_storage` call + `self.storage`
  attribute. Keep signatures unchanged (platform/proxy compat).
- `worker_modal_cls_small_vision.py`: `_run_analyze` (L68) →
  `_do_inference`; `analyze_web` (L81–88) → delegate to `analyze`.
  Pin modal deps (L32–40: `transformers/torchvision/pillow/accelerate/fastapi/hf_transfer`
  all bare today — pin per spec).
- `worker_beam_eq_small_vision.py`: keep `load_deps` (passes `cache_dir`).
- `worker_flash_cls_small_vision.py`: import/call swap only.
- All 3: import/call swap `run_analyze` → `do_inference`.

## 4. Verify

- `pytest workers/vision -v` green, unmodified tests.
- `-m local_e2e workers/vision` green; then deploy test env, `-m deployed_e2e
  workers/vision` green, undeploy.
- Negative check + output-model keys ⊆ `contracts/*.json`.
- `rg "run_analyze|require_storage" workers/vision` → zero hits.
- `ruff check` clean. No test over ~25 lines.

## 5. Commit

`test(workers): add vision unit + e2e tests per worker file` +
`refactor(workers): lean vision workers on do_inference, drop dead storage`.
