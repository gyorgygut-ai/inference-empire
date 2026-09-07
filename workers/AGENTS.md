# GPU Workers

## Golden Rules

- Use conventional commits
- Specs are authoritative: code must match them
- Exact touched files and lines to finish task; no less, no more
- Adherence to specs, key decisions and golden rules is non-negotiable

---

## Master Worker List

Every worker type must be implemented for all 3 providers (Flash, Beam, Modal).

- Flux2: async, 4 steps, cfg 1, produces artifact
- H3-FL2VA: async, 50 steps, produces artifact
- H3-REF2VA: async, 50 steps, produces artifact
- H3-REF2VA-COMFY: async, 20 steps, scheduler=simple, produces artifact
- Krea2: sync, 8 steps, cfg 0.0, produces artifact
- tiny-sd: sync, 20 steps, cfg 7.5, produces artifact
- Vision: sync, produces JSON
- Voice: async, realtime streaming

---

## Naming Convention

```
worker_{platform}_{pattern}_{model}.py
```

**Platform:** `flash`, `beam`, `modal`

**Patterns:**

- Flash: `qb` (queue), `lb` (routes), `cls` (class), `pre` (pre-built)
- Beam: `fn` (function), `eq` (endpoint), `tq` (task queue), `asgi`, `pod`
- Modal: `fn` (function), `cls` (class), `fe` (fastapi endpoint), `asgi`

---

## Worker Behaviour

- All workers creating an artifact must upload to R2 and return access to it
- Not all workers produce artifacts; some just return json directly
- Production deps are inline in worker files, not in pyproject.toml

---

## Contracts

- Contract JSON lives in `contracts/{name}.json` — source of truth
- Every `input` and `output` schema MUST declare a non-empty `required` array
- A field is optional ONLY if it has a `default`
- Update JSON first, then update worker pydantic models to match
- Rules implemented as pydantic validators in the worker, against the JSON

---

## Dependency Constraints & Shims

- Pin ALL deps to exact versions. Never use bare package names.
- Krea2 workers: `transformers>=4.57,<5` with `diffusers==0.39.0`
- Flux2 workers: `transformers>=5.0,<6` with `diffusers==0.40.0`
- **Torch load shim** (required for flash/beam/modal):
  ```python
  import torch.distributed as dist
  dist.is_available = lambda: False
  ```
- **Async by default for long tasks**: Long-running tasks (>30s) MUST use async patterns. Beam: `tq` not `eq`. Modal: `.spawn()` not webhooks. Sync only for tasks <30s.

---

## Flash Rules

- `import torch` INSIDE function body, never at module level
- Declare deps in `@Endpoint(dependencies=[...])`, not pyproject.toml
- `workers=N` is shorthand for `(0, N)`
- Class workers: model loading in `__init__`, request handling in instance methods
- Cross-worker calls use `await`
- System packages (ffmpeg) go in `system_dependencies`
- `flashboot=True` for all stateful workers

---

## Beam Rules

- One worker per file
- Decorated function with `on_start` for pipeline loading
- Pydantic `BaseModel` inputs/outputs use `ConfigDict(title=...)`
- Image: Python 3.11/3.10, exact pinned deps, system packages (`ffmpeg`), env (`HF_HOME`, `HF_HUB_ENABLE_HF_TRANSFER=1`)
- Volumes: use `Volume` for caching models across cold starts (`./hf-cache`)
- Compute: smallest GPU that fits (`RTX4090` default), timeout 300s (or 3600s for video), memory 32-64Gi, checkpoint_enabled=True for task queues
- Concurrency: `max_containers=1` for GPU workers, no concurrent execution for model inference (serialize with `threading.Lock`)
- Secrets: create before deploy (`beam secret create`)

---

## Modal Rules

- App with `@app.cls` and `@modal.enter()`-loaded pipeline
- Pydantic `BaseModel` inputs/outputs use `ConfigDict(title=...)`
- Image: `modal.Image.debian_slim(python_version="3.11")`, pin deps, set `HF_HOME` and `HF_HUB_ENABLE_HF_TRANSFER=1`, use `modal.Volume` + `@modal.enter()` for model caching
- Compute: smallest GPU that fits (`L4` default), `scaledown_window` 60–150s, `max_containers=1`, timeout 300s (3600s for voice/video)
- Concurrency: no `@modal.concurrent` for inference, serialize with `threading.Lock`
- Endpoints: `@app.cls` workers invoked via `modal.Cls.from_name().().method.remote()` or `.spawn()`

---

## Commands

### Flash

- Local dev: `flash dev`
- Deploy: `flash deploy` (or `flash deploy --name <name>`)
- Preview: `flash deploy --preview`
- Tear down: `flash undeploy` (or `flash undeploy --name <name>`)

### Beam

- Local dev: `beam serve`
- Deploy: `beam deploy <file>` (or `beam deploy` for all)
- Logs: `beam logs`

### Modal

- Deploy: `modal deploy <file>` (or `modal deploy`)
- Invoke: `modal.Function.from_name("app","method").spawn(...)` (do not use `modal run`)

---

### Undeploy

- Flash: `flash undeploy`
- Beam: `beam worker stop --name <name>` (or `beam worker stop --all`)
- Modal: `modal app stop <app-name>` (use `stop`, never `destroy`)

### Task Cancellation

- Beam: `beam task list` → `beam task stop <task-id>`
- Beam (all pending): `beam task list | grep PENDING | awk '{print $1}' | xargs beam task stop`
- Modal: N/A (`spawn()` + `.result()` tasks are not independently cancellable)

### Logging & Polling

- Beam single task: `beam logs --task-id <id>`
- Beam worker tasks: `beam logs --stub-id <name>`
- Beam poll async task (owner live runs): `beam logs --task-id <id> --timeout 3600 --follow` (wait for `[OK]` or `[ERR]`)
- Modal app logs: `modal app logs <app-name>`
- Modal container logs: `modal container logs <container-id>`

Log tag order: `[INIT]` → `[REQ]` → `[GEN]` → `[R2]` → `[OK]` (or `[ERR]`).

---

## Test Strategy

### Run All Tests

- Fake (mocked inference, local): `uv run --locked pytest workers/`
- Per model: `uv run --locked pytest workers/<model>/tests/`

### Run Per-Worker Tests

- Single worker: `uv run --locked pytest workers/<model>/tests/test_<worker-name>.py -k "<test>"`

### Test + Code Rules

- Use `pytest` + `tests` folder
- One test file per worker
- Each worker file must have e2e tests
- Any worker change must result in a failing test
- Tests focus on set input -> expected output
- Task finished when tests pass, without shortcuts

---

## Unit Tests

**Rules:**

- Tests-first worker architecture with `_shared_*` file in worker folder
- `load_dependencies` and `do_inference` always used from shared
- `load_dependencies` mocked with fakes to avoid side effects

**Cases:**

- [ ] Inference requested with right args
- [ ] Fake bucket has "uploaded" artifact
- [ ] `do_inference` returns output contract

---

## E2E Tests

**Tests:**

- [ ] Iterate via local dev commands
- [ ] Invalid input: should reject
- [ ] Good input: should return contract + artifact must exist in bucket (if applicable)
