# Local E2E Tiny Fix — close gaps, ship real tiny e2e, no canned

## Current state summary
- Mock servers, local platforms, local runners, tiny loaders, dep_check exist
- Tests still inject canned fakes (`FakeImagePipe(canned)`, `FakeVisionModel(CANNED)`)
- Dep parity code exists but is not run pre-flight
- Acceptance is canned equality, not contract + artifact
- Isolation of fake dicts per module is implicit, not enforced

## Goals
- `pytest workers/ --target fake` runs real tiny inference for all workers
- No canned outputs in e2e path, no env vars, no flags, no worker edits
- Dep parity fails fast before inference
- Contract + artifact acceptance only

## Changes — zero worker edits, wiring and tests only

### 1. Test migration: replace canned deps with tiny deps
For each `test_e2e_*.py`:
- Remove `Fake*` imports
- Import tiny loaders:
  Image workers → `from workers.services.inference.tiny_image import load_tiny_image_pipe`
  Vision workers → `from workers.services.inference.tiny_vision import TinyVisionModel, TinyVisionProcessor`
  Video/H3 workers → `from workers.services.inference.tiny_video import load_tiny_video_pipe, write_video_audio`
- Build deps tuple to match each worker’s `generate` signature:
  Image: `(bucket, load_tiny_image_pipe(), FakeTorchModule())`  # torch fake is fine, pipe is real
  Vision: `(TinyVisionModel(), TinyVisionProcessor(), prompt)`
  Video: `(bucket, load_tiny_video_pipe(), write_video_audio, ...)`
- Keep `FakeR2Storage` for bucket, keep `FakeTorchModule` where the worker calls `torch.cuda.is_available()` only
- Change assertions:
  - Invalid input → `pytest.raises(Exception, match=...)`
  - Good input → `out = e2e_target.run(...)`
    - Assert contract keys present per `contracts/{name}.json`
    - If artifact present → `bucket.has(key)` and `bucket.fetch(key)` returns non-empty bytes
    - Do NOT assert exact pixel/text equality

### 2. Pre-flight dep parity
- Add to `conftest.py` local path:
  In `e2e_target` fixture, before returning `LocalTarget`, call:
  `workers.services.deps.dep_check.check_worker(worker_path_for(request.node.fspath))`
- This runs extract pins via AST, checks exact pins, python 3.11, ffmpeg, torch shim
- Failure message must name the worker and the mismatched pin

### 3. Fake dict isolation
- `local_fake_session` currently deploys all three platforms once per session
- Add per-module clear in `deployed_worker` / `LocalTarget` teardown:
  After each module, call `flash_fake.clear()`, `beam_fake.clear()`, `modal_fake.clear()`
- Prevents cross-test leakage of JOBS dict

### 4. Runner / Target alignment
- Keep `workers/e2e_targets.py LocalTarget` as is
- Ensure `LocalTarget.run` and `run_async` pass `deps` through `load_dependencies` seam only
- No changes to production `workers/e2e_targets.py deploy/undeploy` paths

### 5. Pin bare deps
- Audit all `worker_*.py` `@Endpoint(dependencies=...)`, `add_python_packages([...])`, `.pip_install(...)`
- Pin any bare name: `safetensors`, `huggingface_hub` → `==x.y.z`
- Narrow `transformers>=5.0,<6` to exact where possible per worker
- Krea2 vs Flux2 split stays enforced per worker

## Execution order
1. Vision tests → green with tiny_vision, contract only
2. Flux2/Krea2 image tests → green with tiny_image, PNG artifact in bucket
3. H3 video tests → green with tiny_video, mp4 artifact in bucket
4. Full suite `pytest workers/ --target fake -q`

## Acceptance criteria per worker
- Invalid input rejects with validation error
- Good input returns dict matching `contracts/{name}.json` required fields
- Artifact key exists in `FakeR2Storage` and fetch returns bytes >0
- Dep parity passes before inference
- Fake dict empty after module teardown

## Verify commands
python -m pytest workers/vision/tests/ --target fake -x -q
python -m pytest workers/flux2/tests/ --target fake -x -q
python -m pytest workers/krea2/tests/ --target fake -x -q
python -m pytest workers/h3/tests/ --target fake -x -q
python -m pytest workers/ --target fake -q
