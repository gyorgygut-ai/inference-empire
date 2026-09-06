# Phase 1 — Flux2 (pilot worker type)

Files: `workers/flux2/_shared_flux2_klein9b.py`,
`worker_{beam_tq,flash_cls,modal_cls}_flux2_klein9b.py` + 3 test files.

Order is TDD: tests first (RED), then rename + cleanup (GREEN).

Pilot finding (settled, copy blindly): provider wrappers are undrivable
in-process (beam's `_CallableWrapper` needs a live queue, flash's
`RemoteClassWrapper` proxies everything remote; modal `.local()` works but
drags provider machinery). So every worker file exposes module-level
`generate(storage, pipe, torch_module, **kwargs)` — validate at boundary,
delegate to `do_inference`, return output contract. Decoration stays purely
deploy-surface: beam's decorated entry is renamed `dispatch`, flash/modal
classes delegate one line. Tests call module `generate` directly with fakes —
no mocks at all. No external code references the beam entry name (no
`WorkerSpec` instances exist yet; queue identity is the `name=` param).

## 1. Tests first (RED) — the enforced shape, ~20 lines each

New files (one test file per worker file — no deviation):

- `workers/flux2/tests/__init__.py` (empty — package, avoids import-mode surprises)
- `workers/flux2/tests/test_worker_beam_tq_flux2_klein9b.py`
- `workers/flux2/tests/test_worker_flash_cls_flux2_klein9b.py`
- `workers/flux2/tests/test_worker_modal_cls_flux2_klein9b.py`

Template (setup / blank / act / blank / assert — nothing else, one assert):

```python
def test_generate_serves_canned_image(bucket):
    canned = PIL.Image.new("RGB", (8, 8), (255, 0, 0))
    pipe, torch_module = FakeImagePipe(canned), FakeTorchModule()

    out = worker_mod.generate(bucket, pipe, torch_module, prompt="a red square", ...)

    assert bucket.fetch(key_of(out)) == png_bytes_of(canned)
```

- No mocks: fakes are constructed directly in setup. Source fake takes its
  canned response in the ctor (`FakeImagePipe(canned)` — required, no default).
- One assert: `fetch` raises on a missing key, so presence + exact bytes in
  a single shot. No `endswith`, no second assert.
- Invalid input (e.g. missing `prompt`) → `pydantic.ValidationError`
  propagates unwrapped (validation sits outside the `try`; own one-assert
  test each).
- `key_of(out)`: parse the key back out of `out["artifact"]["presigned_url"]`
  (fake URL shape is `{base}/{key}`); `png_bytes_of(canned)`: re-encode the
  canned image to PNG — that is expected-value construction, not fake prep.

Run `pytest workers/flux2` → **fails** (module `generate` does not exist
yet). Red confirmed. All three worker modules import offline (proven:
beam/modal/flash SDKs execute decorators without network).

## 1b. E2E tests (same bodies, `e2e_target` + `bucket`)

- `workers/flux2/tests/test_e2e_worker_beam_tq_flux2_klein9b.py` (uses
  `run_async` — `tq` polls for real)
- `workers/flux2/tests/test_e2e_worker_flash_cls_flux2_klein9b.py` (uses `run`)
- `workers/flux2/tests/test_e2e_worker_modal_cls_flux2_klein9b.py` (uses `run_async` — spawn path)

Template: setup builds `canned` + `deps = (FakeImagePipe(canned),
FakeTorchModule())`; act is one target call —
`e2e_target.run(worker_mod, inputs, deps, bucket)` /
`e2e_target.run_async(worker_mod, inputs, deps, bucket)`; assert identical
to unit. Each marked `@pytest.mark.local_e2e` / `@pytest.mark.deployed_e2e`
(same body, marker picks the rung). One assert each.

## 2. Shared cleanup (`_shared_flux2_klein9b.py`)

- L114: `def run_generate(` → `def do_inference(`. Signature unchanged:
  `(pipe, torch_module, storage: Storage, req: Flux2Klein9bInput)`.
- Nothing else — shared is already lean. `load_pipeline_as_needed` stays.

## 3. Worker cleanup — module `generate` + thin deploy surface in each file

Each file gains module-level `generate(storage, pipe, torch_module,
**kwargs)` (validate outside the `try`, delegate to `do_inference`, return
output contract, `[ERR]` print + `raise RuntimeError(...) from e`); the
decorated entry delegates one line.

### `worker_beam_tq_flux2_klein9b.py`

- Delete `_load_dotenv` (L24–37) → move a single copy into `_shared` as
  `ensure_dotenv()` helper, one-line call at import. (Same helper duplicated
  in krea2 beam — each `_shared` gets its own copy; no cross-model imports.)
- Delete dead `START = time.time()` (L21, never read).
- Delete `load_deps` wrapper (L66–67) → `on_start=load_dependencies`
  directly (flux2 takes no `cache_dir`; the wrapper adds nothing).
- Rename decorated `generate` → `dispatch` (queue identity is the `name=`
  param, untouched); body becomes
  `return generate(storage, *context.on_start_value, **kwargs)`.
- Import/call swap to `do_inference` (L10–14) — the call lives in module
  `generate` now.

### `worker_modal_cls_flux2_klein9b.py`

- Delete broken `main()` local entrypoint (L24–42): constructs
  `FluxKleinWorker()` with no `storage` → `TypeError`. Dead code.
- `FluxKleinWorker.generate` → one-line delegate to module `generate`;
  `generate_web` → `return generate(self.storage, self.pipe,
  self.torch_module, **item.model_dump())`.
- Delete dead `START_TIME` (L21).
- Import swap to `do_inference` (L9–13) — the call lives in module
  `generate` now.

### `worker_flash_cls_flux2_klein9b.py`

- `FluxKleinWorker.generate` → one-line delegate to module `generate`.
- Pin deps per the spec flux2 rule (`transformers>=5.0,<6` with
  `diffusers==0.40.0`). Current `dependencies` list is wrong/bare:
  `transformers>=4.57,<5` (wrong family), bare `diffusers`, `accelerate`,
  `sdnq`, `pillow`, `boto3`. Target: `torch==2.9.1`,
  `diffusers==0.40.0`, `transformers>=5.0,<6`, `accelerate==1.14.0`,
  `sdnq==0.2.6`, `safetensors`, `huggingface_hub`, `pillow==12.3.0`,
   `boto3==1.43.83` — mirror the beam image list.
- Import swap to `do_inference` (L8–12) — the call lives in module
  `generate` now.

## 4. Verify

- `pytest workers/flux2 -m "not deployed_e2e" -v` green — pilot tests pass
  **unmodified**, proving the seam. (Plain `pytest` would also select the
  `deployed_e2e` twins, which rightly fail loud without `TEST_ENV_URL`.)
- `-m local_e2e workers/flux2` green; then deploy test env, `-m deployed_e2e
  workers/flux2` green, undeploy.
- Negative check: break an output-contract key → test fails (proves
  "change → failing test"). Output-model keys ⊆ `contracts/*.json`.
- `rg "run_generate|run_analyze" workers/flux2` → zero hits.
- `ruff check` on all touched files. No test over ~25 lines.

## 5. Commit

`test(workers): add flux2 unit + e2e tests per worker file` (tests) then
`refactor(workers): lean flux2 workers on do_inference` (rename + cleanup).
Or a single phase commit if preferred at execution time.
