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

Only these patterns exist in the repo — do not invent others:

- Flash: `cls` (plus one `pre` exception for h3-ref2va-comfy)
- Beam: `tq` (plus `asgi` for realtime voice only)
- Modal: `cls`

---

## Worker Behaviour

- All workers creating an artifact must upload to R2 and return access to it
- Production deps live in `_shared_*IMAGE_PIP_DEPS`, never inline in worker files, never in pyproject.toml

---

## Contracts

- Contract JSON lives in `contracts/{name}.json` — source of truth
- Every `input` and `output` schema MUST declare a non-empty `required` array
- A field is optional ONLY if it has a `default`
- Update JSON first, then update worker pydantic models to match

---

## Dependency Constraints & Shims

- Pin ALL deps to exact versions. Never use bare package names.
- Krea2 workers: `transformers>=4.57,<5` with `diffusers==0.39.0`
- Flux2 workers: `transformers>=5.0,<6` with `diffusers==0.40.0`
- **Single source of pins**: each model family's image pip deps live in exactly
  one place — `IMAGE_PIP_DEPS` in its `_shared_*` module. Modal uses
  `.pip_install(*IMAGE_PIP_DEPS)`, Beam uses `.add_python_packages(list(IMAGE_PIP_DEPS))`,
  Flash uses `dependencies=list(IMAGE_PIP_DEPS)`. Comfy families use a pinned
  registry image on Modal/Beam; only their Flash worker uses `IMAGE_PIP_DEPS`.
- **Pre-deploy gate (mandatory)**: resolve the family's pin set in isolation
  before any deploy. One line per family, e.g. Krea2:
  ```bash
  uv run python -c "from workers.krea2._shared_krea2_ref2img import IMAGE_PIP_DEPS; print('\n'.join(IMAGE_PIP_DEPS))" | uv pip compile --python-version 3.11 -
  ```
  Non-zero exit = do not deploy, fix the table. Voice tables live in
  `workers/voice/_shared_voice_chat.py` (one per runtime: `REALTIME`,
  `CHATTERBOX`, `OPENVOICE`, `QWEN`, `CHAT`); the `QWEN` table targets a
  python3.10 image, so gate it with `--python-version 3.10`.
- **Torch load shim** (required for flash/beam/modal):
  ```python
  import torch.distributed as dist

  def _dist_unavailable() -> bool:
      return False

  setattr(dist, "is_available", _dist_unavailable)
  ```
- **Async by default for long tasks**: Long-running tasks (>30s) MUST use async patterns. Beam: `tq`. Modal: `.spawn()`. Sync only for tasks <30s.

---

## Flash Rules

- Never `import torch` at module level in worker files
- Declare deps in `@Endpoint(dependencies=[...])`, not pyproject.toml
- Class workers: model loading in `__init__`, request handling in instance methods
- `workers=(0, 1)` and `flashboot=True` for all stateful workers

---

## Beam Rules

- One worker per file
- Decorated function with `on_start` for pipeline loading
- Pydantic `BaseModel` inputs/outputs use `ConfigDict(title=...)`
- Volumes: use `Volume` for caching models across cold starts (`./hf-cache`)
- `checkpoint_enabled=True` for task queues
- Serialize model inference with `threading.Lock`, `max_containers=1`

### Beam task_queue invocation

```python
task = worker_mod.dispatch.put(**GOOD)
out = task.result(wait=True)
```

---

## Modal Rules

- App with `@app.cls` and `@modal.enter()`-loaded pipeline
- Pydantic `BaseModel` inputs/outputs use `ConfigDict(title=...)`
- Image: `modal.Image.debian_slim(python_version="3.11")`, pin deps, set `HF_HOME` and `HF_HUB_ENABLE_HF_TRANSFER=1`, use `modal.Volume` + `@modal.enter()` for model caching
- Compute: smallest GPU that fits (`L4` default), `scaledown_window` 60–150s, `max_containers=1`, timeout 300s (3600s for voice/video)
- Concurrency: no `@modal.concurrent` for inference, serialize with `threading.Lock`
- Endpoints: `@app.cls` workers invoked via `modal.Cls.from_name().().method.remote()` or `.spawn()`

---

## Workflow

Log tag order for all providers: `[INIT]` → `[REQ]` → `[GEN]` → `[R2]` → `[OK]` (or `[ERR]`).

### Modal — deploy / run / logs (verified live)

Each Modal e2e file carries its own module-scoped `deployed_app` fixture
(`modal deploy` on setup, `modal app stop` on teardown). No shared fixtures.

Deploy:

```bash
uv run --locked modal deploy workers/<model>/worker_modal_cls_*.py
```

Run manually (no tests):

```python
Cls = modal.Cls.from_name("<app>", "<Cls>")  # e.g. tiny-sd-worker / TinySDWorker
call = Cls().generate.spawn(**GOOD)  # e.g. {"prompt": "a red square", "seed": 7}
out = call.get(timeout=300)
```

Logs — poll every 10s while waiting:

```bash
modal app logs <app> --since <iso-start> --timestamps --tail 50
```

When something fails: `[ERR]` in logs + `call.get()` raises → re-check logs with `--since`, fix, redeploy. Tear down with `modal app stop <app> --yes`.

### Beam — run / logs

No deploy step and no fixtures: `.put()` deploys on demand directly in Python.

Run:

```python
task = worker_mod.dispatch.put(**GOOD)
out = task.result(wait=True)  # None means check beam logs
```

Logs — poll while waiting:

```bash
beam logs --stub-id <name>
```

When something fails: `out is None` or `[ERR]` in logs → inspect `on_start` / `dispatch` body, fix, re-run.

### Flash — deploy / run (dev unavailable)

`flash dev` is not available. E2E files skip at file level
(`pytestmark = pytest.mark.skip(reason="flash dev not available")`).

```bash
flash deploy --name <name>
flash undeploy --name <name>
```

Run in-process: `TinySDWorker().generate(**GOOD)`. When something fails: `[ERR]` → check `.flash/logs/activity.log`, fix `@Endpoint(dependencies=[...])`, redeploy.

---

## Test Strategy

Verified commands (see `workers/VERIFICATION.md` — 245 unit passed):

- All unit: `uv run --locked pytest workers/ -k "not e2e"`
- Per model unit: `uv run --locked pytest workers/<model>/tests/ -k "not e2e"`
- All e2e: `uv run --locked pytest workers/ -k "e2e"`
- Per model e2e: `uv run --locked pytest workers/<model>/tests/ -k "e2e"`

Rules:

- Tests focus on set input -> expected output
- Non-voice workers have e2e files; voice workers are unit-only (no e2e)

---

## Unit Tests

**Rules:**

- Non-voice: `_shared_*` file in worker folder with `load_dependencies` and `do_inference`
- `load_dependencies` mocked with fakes to avoid side effects

**Cases:**

- Inference requested with right args
- Artifact workers: mock bucket has "uploaded" artifact (N/A for Vision JSON)
- `do_inference` returns output contract

---

## E2E Tests

- Good input: should return contract + artifact must exist in bucket (if applicable)
