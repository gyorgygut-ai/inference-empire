# Phase 0 — Harness + service/fake pairs (once, first)

## Goal

Re-establish the minimal pytest setup the factory purge removed, harden every
service into its final interface/service/fake shape, and lock the global test
rules before any worker phase starts.

## Global rules (apply to every phase below, non-negotiable)

1. **One interface per service, fully implemented by both sides.** Three files
   per service: interface, service, fake. The fake is functional (in-memory
   store / seeded responder), never a record-and-verify mock.
2. **Sinks vs sources.** Sink fakes (storage) take no constructor prep — they
   receive shit and serve shit; tests assert "the bucket has exactly this".
   Source fakes (inference) *require* the canned response in the constructor
   ("respond with exactly this when requested").
3. **Tests are stupid-simple:** setup, blank line, act, blank line, assert.
   No object-creation gymnastics, no long test functions, no magic. This goes
   for conftest fixtures too. A test over ~25 lines means the fake is wrong —
   fix the fake, not the test.
4. **Assert on output data only.** Stored/served bytes and returned contracts.
   No mocks except the `load_dependencies` seam (and transport-level for
   comfy). No call assertions — no `_calls` logs exist anywhere to assert on.

## Ops

### P0.1 — Re-add pytest config (`pyproject.toml`)

Insert after the `[tool.setuptools.packages.find]` block, before `[tool.ruff]`:

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["workers"]
markers = [
    "local_e2e: end-to-end against canned fakes, in-process",
    "deployed_e2e: end-to-end against the test-env deployment",
]
```

`pytest` itself is still in dev deps — no install change.

### P0.2 — New minimal `workers/conftest.py` + `workers/e2e_targets.py`

Conftest (ONLY this — 2 fixtures, ≤5 lines each):

```python
import os

import pytest

from workers.e2e_targets import DeployedTarget, LocalTarget
from workers.services.storage.r2_storage_fake import FakeR2Storage


@pytest.fixture
def bucket():
    return FakeR2Storage()


@pytest.fixture
def e2e_target(monkeypatch, request):
    if request.node.get_closest_marker("deployed_e2e"):
        return DeployedTarget(os.environ["TEST_ENV_URL"])
    return LocalTarget(monkeypatch)
```

`workers/e2e_targets.py` (one plain module, not a registry — just the two
rung classes with identical `run`/`run_async` methods). The local rung
patches `load_dependencies` (proving the seam — entries resolve deps through
it on deploy) then drives module-level `generate` directly; `run_async`
additionally exercises the submit/poll/result loop via `FakeAsyncRunner`
over a tiny private adapter (not a registry — one 4-line shim):

```python
class LocalTarget:
    def __init__(self, monkeypatch):
        self.monkeypatch = monkeypatch

    def _deps(self, worker_mod, deps):
        self.monkeypatch.setattr(worker_mod, "load_dependencies", lambda **k: deps)
        return worker_mod.load_dependencies()

    def run(self, worker_mod, inputs, deps, storage):
        return worker_mod.generate(storage, *self._deps(worker_mod, deps), **inputs)

    def run_async(self, worker_mod, inputs, deps, storage):
        pipe_deps = self._deps(worker_mod, deps)
        call = lambda: worker_mod.generate(storage, *pipe_deps, **inputs)
        runner = FakeAsyncRunner()
        return runner.result(runner.submit(_Fn(call), **inputs))


class _Fn:
    def __init__(self, call):
        self._call = call

    def generate(self, **inputs):
        return self._call()


class DeployedTarget:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")

    def run(self, worker_mod, inputs, deps, storage):
        return post_and_poll(self.base_url, worker_mod, inputs, sync=True)

    def run_async(self, worker_mod, inputs, deps, storage):
        return post_and_poll(self.base_url, worker_mod, inputs, sync=False)
```

No hooks. No `pytest_addoption`. No `--target` flag. No AST/magic of any kind.
The marker is the rung switch (`-m local_e2e` / `-m deployed_e2e`); the only
env var is `TEST_ENV_URL` (an address, not a switch).

### P0.3 — Service/interface/fake hardening (3 files per service)

No more "real vs fake" naming. The service and the fake *of that service*:

| dir | interface (untouched) | service (renamed from `real_*`) | fake |
|---|---|---|---|
| `storage/` | `storage.py` (`Storage`) | `r2_storage.py` (`R2Storage` + `require_storage`, moved from `real_r2.py`) | `r2_storage_fake.py` (`FakeR2Storage`, no-arg ctor) |
| `torch_module/` | `torch_module.py` (`TorchModule` protocol — stays, both sides implement it) | `torch_module_service.py` (`TorchModuleService`: keeps dist-shim in `__init__`, delegates everything else to real torch via `__getattr__`) | `torch_module_fake.py` (shape-correct `FakeTorchModule`: `Generator(device).manual_seed(seed)` no-op, `cuda.is_available()` → False) |
| `write_video_audio/` | `write_video_audio.py` (`WriteVideoAudio`) | `write_video_audio_service.py` (`WriteVideoAudioService`, wraps diffsynth) | `write_video_audio_fake.py` (`FakeWriteVideoAudio(payload)` — payload **required**, written to `output_path`, `_calls` log deleted) |
| `runner/` | **new** `runner.py` (`Runner` interface — does not exist yet, gets written) | `runner_service.py` (ex-`real_runners.py`, `Real` prefix dropped) | `runner_fake.py` (ex-`fake_runners.py`) |
| `platform/` | `spec.py` (already the interface) | class `Real` prefixes dropped (`RealBeamPlatform` → `BeamPlatform`, etc.) | untouched |
| `inference/` (**new**) | n/a — the service side is each model's `load_pipeline` | n/a | `image_pipe_fake.py` (`FakeImagePipe(image)` — `__call__(**kw)` returns `images=[image]`), `vision_fake.py` (`FakeVisionModel(result)` + `FakeVisionProcessor(result)`, decode returns `json.dumps(result)`), `video_pipe_fake.py` (`FakeVideoPipe(frames, audio)`) |

Rewire every import in workers/shared/`__init__` re-exports to the new paths.
The `TorchModuleService` delegation is a live-path behavior change — flagged,
in scope (goal is working workers end to end, no exceptions).

### P0.4 — Hygiene (filesystem only, all gitignored)

```bash
rm -rf workers/*/__pycache__ workers/*/.pytest_cache
```

## Verify

- `pytest --collect-only` runs (0 tests collected, no config error).
- `rg "RealR2Storage|RealTorchModule|RealWriteVideoAudio|RealFlash|RealBeam|RealModal|_calls|real_r2|torch_module_real|write_video_audio_real|real_runners|fake_runners" workers` → zero hits.
- `python -c` imports every interface + service + fake.
- `git status --short` shows only service renames/adds + `M pyproject.toml` + `?? workers/conftest.py` + `?? workers/e2e_targets.py`.

## Commit

`refactor(workers): service/interface/fake pairs, drop Real naming` then
`test(workers): add pytest config, markers, conftest and e2e targets`
