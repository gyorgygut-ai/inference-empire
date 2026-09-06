# Phase 2 — Krea2

Files: `workers/krea2/_shared_krea2_ref2img.py`,
`worker_{beam_tq,flash_cls,modal_cls}_krea2_ref2img.py` + 3 test files.

Same TDD order as Phase 1: tests first (RED), then rename + cleanup (GREEN).
Same stupid-simple shape: setup / blank / act / blank / assert, ~20 lines,
assert on contract + exact stored bytes.

## 1. Tests first (RED)

- `workers/krea2/tests/__init__.py` (empty)
- `workers/krea2/tests/test_worker_beam_tq_krea2_ref2img.py`
- `workers/krea2/tests/test_worker_flash_cls_krea2_ref2img.py`
- `workers/krea2/tests/test_worker_modal_cls_krea2_ref2img.py`

Same template as flux2 (one assert): `monkeypatch` `load_dependencies` →
`(FakeImagePipe(canned), runtime_dir, FakeTorchModule())`, drive `generate`,
assert `bucket.fetch(key_of(out)) == png_bytes_of(canned)`; invalid input →
`pydantic.ValidationError` (own one-assert test). Fails on import until the rename lands.

## 1b. E2E tests (same bodies, `e2e_target` + `bucket`)

- `workers/krea2/tests/test_e2e_worker_beam_tq_krea2_ref2img.py` (`run_async`)
- `workers/krea2/tests/test_e2e_worker_flash_cls_krea2_ref2img.py` (`run`)
- `workers/krea2/tests/test_e2e_worker_modal_cls_krea2_ref2img.py` (`run_async`)

Marked `@pytest.mark.local_e2e` / `@pytest.mark.deployed_e2e`. One assert each.

## 2. Shared cleanup (`_shared_krea2_ref2img.py`)

- L190: `def run_generate(` → `def do_inference(`. Signature unchanged:
  `(pipe, runtime_dir, torch_module, storage: Storage, req)`.
- Nothing else — shared is already lean.

## 3. Worker cleanup

### `worker_beam_tq_krea2_ref2img.py`

- Delete `_load_dotenv` (L20–33) → shared `ensure_dotenv()` helper (same
  treatment as flux2 Phase 1).
- **Signature fix:** `generate()` takes explicit kwargs (L86–98). Switch to
  `**kwargs` + `Krea2Ref2ImgInput(**kwargs)` like every other worker — today
  adding an Input field requires editing the signature by hand.
- Keep the `load_deps` wrapper (passes `cache_dir=CACHE_PATH` — earns its keep).
- Import/call swap to `do_inference` (L9–13, L113).

### `worker_modal_cls_krea2_ref2img.py`

- `generate_web` (L111–119) → delegate to `generate`.
- `_download_models` (L27–45): verify at execution whether anything wires it
  (vision modal wires its downloader via `.run_function`; krea2 modal does
  not). Delete if unwired.
- Import/call swap to `do_inference` (L9–15, L104, L114).

### `worker_flash_cls_krea2_ref2img.py`

- Pin deps per the krea2 rule (`transformers>=4.57,<5` with
  `diffusers==0.39.0` — family correct, `diffusers` bare). Pin
  `accelerate/safetensors/pillow/protobuf/opencv-python-headless/peft/boto3/huggingface_hub`
  to the beam worker's exact versions.
- Import/call swap to `do_inference` (L8–12, L60–62).

## 4. Verify

- `pytest workers/krea2 -v` green, unmodified tests.
- `-m local_e2e workers/krea2` green; then deploy test env, `-m deployed_e2e
  workers/krea2` green, undeploy.
- Negative check + output-model keys ⊆ `contracts/*.json`.
- `rg "run_generate" workers/krea2` → zero hits. `ruff check` clean.
- No test over ~25 lines.

## 5. Commit

`test(workers): add krea2 unit + e2e tests per worker file` +
`refactor(workers): lean krea2 workers on do_inference`.
