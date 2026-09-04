# GPU Workers

## Critical Specs - Read Before Doing Anything

Read this entire file before working on any worker.

---

## Golden Rules

- Specs are authoritative: code must match them
- Exact touched files and lines to finish task; no less, no more
- Adherence to specs, key decisions and golden rules is non-negotiable
- No shortcuts, skimming, fabricating or lying; if task not clear, say it
- Use conventional commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`

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

- One worker per file: `worker_{platform}_{pattern}_{model}.py`
- App with `@app.cls` and `@modal.enter()`-loaded pipeline
- Pydantic `BaseModel` inputs/outputs use `ConfigDict(title=...)`
- Image: `modal.Image.debian_slim(python_version="3.11")`, pin deps, set `HF_HOME` and `HF_HUB_ENABLE_HF_TRANSFER=1`, use `modal.Volume` + `@modal.enter()` for model caching
- Compute: smallest GPU that fits (`L4` default), `scaledown_window` 60–150s, `max_containers=1`, timeout 300s (3600s for voice/video)
- Concurrency: no `@modal.concurrent` for inference, serialize with `threading.Lock`
- Endpoints: `@app.cls` workers invoked via `modal.Cls.from_name().().method.remote()` or `.spawn()`

---

## Gotchas

- Flash: `flash dev` bundles ALL `@Endpoint` files in current directory. Each Flash folder is isolated.
- Modal/Beam: target specific files, no per-folder constraint.
- Production deps are inline in worker files. Local venv is for IDE/tests only.
- Testing for status `200` only means the platform fired up the worker.

---

See [COMMANDS.md](./COMMANDS.md) and [Testing Specs](./TESTING.md)
