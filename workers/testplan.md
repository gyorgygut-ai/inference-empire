# Workers Test Plan

## Goal

One `workers/` root holding every model dir (`flux2`, `krea2`, `h3`, `vision`,
`voice`) plus shared `services/`, with a single test harness. Same test file
runs mocked locally (`--target fake`) and real on dev (`--target live`) with
zero branching in test bodies. Covers both worker species: request/response
(flux, krea, h3, vision) and realtime WebSocket (voice). Single point of
change for logic, harness, and the local/dev toggle — making future drift
structurally hard, not just unlikely.

## Design principles (non-negotiable)

- Encapsulate together only what changes together. Worker ceremony (GPU type,
  image tag, env, timeouts) stays duplicated per worker — it changes
  independently. What's shared gets verified uniformly instead.
- Mock the backend, not the logic. Fake = canned outputs matching the
  contract + sentinel-triggered failure. No content inspection ever — no image
  decoding, no audio handling, no model weights. Shared `run_*` / `analyze_*`
  / session-event logic stays REAL and under test; only the inference backend
  is stubbed.
- Harness lives in `workers/conftest.py`. Each test file imports its spec
  object (`from workers.<model>.testing import <SPEC> as SPEC`); that import
  is the only per-file wiring. No worker imports in test files, no `if
  target` anywhere outside factories.
- Sync/async is never chosen in test bodies. Bodies call one method,
  `runner.run(worker, **inputs)`. Kind comes from SPEC → factory → runner
  class: a sync-kind runner's `run()` executes direct, an async-kind
  runner's `run()` runs the submit → poll → result path. The test doesn't
  know or choose.
- Factories branch on `target` exactly once. No `if target` anywhere else.
- Same test code + same worker source files run under both targets. The only
  target-conditional code is in conftest factories and `build_proxy`:
  deploy (no-op vs CLI), runner transport (local call / TestClient vs provider
  CLI / live endpoint), storage backend (FakeR2 vs RealR2), model weights
  (stubbed vs real).
- Request/response fakes simulate provider behavior locally (sync = immediate,
  async = task id + poll loop + 10–500ms latency), never `sleep()`-then-return
  stubs. Voice fakes stub the `models` dict; the real app + real session
  handling still run.
- Fake-green never equals live-green by design. Unit tests prove fakes match
  their frozen spec; only live runs prove identity with the provider.
- STRICT RULE: tests are executed with `--target fake` only. Never
  `--target live`, never any dev-target run, no exceptions. Live verification
  is the owner's domain, outside this plan's execution.

## Scope locks (violating these fails the plan)

- Voice is IN: websocket test shape alongside the runner interface, same
  `--target` toggle, same decorator pattern. (`voice/tests/` is empty today —
  new voice tests are written in Todo 3f.)
- `cli/tests/build.py` old-pattern helpers are OUT (different era, untouched).
- `flux2/tests/e2e/`, `vision/tests/e2e/` are empty — no e2e files exist to
  migrate; `specs/COMMANDS.md` lines referencing `e2e_local`/`e2e_dev` are
  aspirational docs, fixed in Todo 1f.
- No test command in this plan targets live/dev. Every Verify block runs
  `--target fake` (or non-test checks like `compileall` / `collect-only`).
  `specs/COMMANDS.md` documents `--target live` as owner-run only.

## Todo 1 — Restructure + package-ify + imports + packaging + docs

**1a. Moves (pure `git mv`, contents untouched).** `mkdir workers`, then
`git mv flux2 workers/flux2`, same for `krea2 h3 vision voice services`.
Per-model `pyproject.toml`, `requirements.txt`, `beam.yaml` (where present),
`contracts/`, `tests/` ride along. Leftovers stay as husks: `h3/.flash/`,
`*/__pycache__/`, empty `e2e/`. Finish with
`git status --porcelain` to confirm husks contain zero tracked files, then
`rm -rf` each husk (`.flash/.build` is a disposable build artifact,
regenerates via `flash build`; `__pycache__` regenerates on import).

**1b. Package-ify (new empty files).** `workers/__init__.py`,
`workers/flux2/__init__.py`, `workers/krea2/__init__.py`,
`workers/h3/__init__.py`, `workers/vision/__init__.py`,
`workers/voice/__init__.py`. (`workers/services/` tree already has them.)
Result: one importable tree — `workers.services.*`,
`workers.flux2.generate_*`. This unlocks Modal's documented sibling path
("if the helper modules are part of that package, you should be all set")
and keeps Flash/Beam resolution trivial.

**1c. Delete the four `tests/__init__.py`** (`flux2 krea2 h3 vision`, all
0 bytes + stale `.pyc`). Reason: four top-level packages all named `tests`
collide in `sys.modules`; without them pytest imports each `tests/` dir in
rootdir mode (unique `test_*` stems, per-dir `conftest` isolation, sibling
worker imports resolve).

**1d. Import rewrites (exact, mechanical).** In every moved `.py`:
`from services.` → `from workers.services.`, `from services import` →
`from workers.services import` (~40 files; all but the `__init__`
re-exports are `TYPE_CHECKING`-only `Storage` under
`from __future__ import annotations` — never evaluated remotely).
`services/*/__init__.py` re-exports updated to `workers.services.*` paths.

**1e. Root `pyproject.toml` (exact edits).**
`packages.find where = ["services"]` → `where = ["workers"]`; add
`[tool.pytest.ini_options]` with `pythonpath = ["."]` and
`testpaths = ["workers"]`; add `modal==1.5.5`, `beam-client==0.2.207` to
`test` extras and pin `runpod-flash==1.7.0` (versions verified installed;
executor re-confirms via `pip freeze`).

**1f. `specs/COMMANDS.md` (exact).** Replace `h3/tests/` pytest invocations
with `workers/<model>/tests/` + `--target fake`; delete/replace the
`e2e_local`/`e2e_dev` lines (those dirs don't exist). Document `--target
live` as owner-run only, never part of this plan's execution.

**Verify (done-gate):** `python -m compileall workers/` clean; `git status`
shows only intended renames + the specified file changes. Collection still
fails on dangling conftest imports — expected, fixed in Todo 3.

## Todo 2 — Factories + fake/real classes (target-only input)

**2a. New factory files (exact signatures, target-only).**
`workers/services/storage/storage_factory.py::storage_factory(target)` →
`FakeR2Storage` / `RealR2Storage`.
`workers/services/platform/platform_factory.py::flash|beam|modal_platform_factory(target)`
→ `Fake*` / `Real*`. Fake deploy = no-op (deploying "turned off"); real =
actual deploy commands (bodies in Todo 5, signatures now).
`workers/services/runner/runner_factory.py` — 6 target-only factories:
`{flash,beam,modal}_{sync,async}_runner_factory(target)` → fake
(simulating) / real (CLI) classes. Runner factory imports modules directly
(`from workers.services.runner.beam_runner import DirectAsyncRunner as
BeamRunner`) — never the `__init__` (it shadows beam's class with modal's).

**2b. Fake runner base (new `workers/services/runner/fake_runners.py`).**
Every runner exposes one method, `run(worker, **inputs)` — test bodies never
choose sync/async. `FakeSyncRunner.run` → `proxy.generate(**kw)` (immediate,
same path as async minus latency). `FakeAsyncRunner.run` → `submit` stores
`(proxy, kw, ready_at=now+uniform(0.01,0.5))` under `task-<8hex>`, `poll`
answers by clock (`IN_PROGRESS`/`COMPLETED`), `result` spins the poll loop
(50ms interval, timeout raises `TimeoutError`). `submit`/`poll`/`result`
stay as the machinery `run()` uses, not as test-facing API.
Per-provider subclasses (`FakeFlashSyncRunner`, …) stay separate by design:
providers deploy and run differently, and things that look alike but change
independently must not be collapsed. Fake voice runners use the same single
`run()` interface where the proxy hides the TestClient websocket exchange.

**2c. Uniform failure rule (all fakes, no exceptions):** any str kwarg
containing `"failure"` (or `type="failure"` for voice) →
`raise RuntimeError("inference failed")`. Matches existing test inputs
(`"invalid_input_that_causes_failure"`); replaces test-name magic
permanently. Vision failure tests switch from the duplicated valid PNG to
the `image_base64="failure"` sentinel at rewrite time (test-input fix, not
a harness change).

**2d. Real classes (skeletons now, bodies Todo 5).**
`Real{Flash,Beam,Modal}{Sync,Async}Runner` exposing single-method `run()`
raising `NotImplementedError` (async kinds keep `submit`/`poll`/`result` as
the machinery `run()` will use); real platforms keep `pass` deploy bodies.
Skeletons exist so Todo 3's fixtures and type references resolve. Per-provider
classes stay separate — providers run differently.

**Verify (done-gate):** `python -c` import of all factories; fake async
round-trip against a dummy proxy
(submit→poll IN_PROGRESS→poll COMPLETED→result) in under 2s.

## Todo 3 — Harness (conftest) + per-model testing.py + test rewrites

All harness machinery lives in `workers/conftest.py`. Tests import their spec
(`from workers.<model>.testing import <SPEC> as SPEC`) and keep the identical
triple `(platform, runner, storage)` plus `platform.create_worker(storage)` +
`runner.run(worker, **inputs)` for every model including voice. No registry,
no markers.

**3a. New `workers/conftest.py` (exact contents).**
`pytest_addoption` (`--target`, default `fake`, choices `fake|live`).
Fixtures: `target`, `spec` (reads `request.module.SPEC`, asserts presence —
a missing `SPEC` import fails at collection, so no coverage test is needed),
`storage` (`storage_factory(target)`), `platform` (provider factory for
`target`, `worker_factory=lambda storage: build_proxy(spec, target, storage,
monkeypatch)`, `deploy()` → yield → `undeploy()`), `runner` (kind factory
for `target`). Plus generic machinery ONLY: `FakeCtx` (attribute bag),
`WorkerSpec` dataclass, `build_proxy(spec, target, storage, monkeypatch)`
(fake→local proxy, live→remote proxy), shared canned-output constants, and
`POLL_INTERVAL=0.05`. No `if target` outside the factories and the
fake/live proxy branch.

**3b. New `workers/<model>/testing.py` ×5 (flux2, krea2, h3, vision, voice —
spec objects only).** Each holds: model canned builders + one `WorkerSpec`
per worker FILE as a module-level object. Spec fields: `{id (identity for
logging), provider, kind, shape, worker_ref/module, method, loader_attr,
pipe_attrs, fake_builder, run_fake_name, run_fake, live_endpoint (None until
Todo 5), input_model}`. Test files import the spec object — never worker
modules. **Delete the 4 model `tests/conftest.py`** (broken
`services.tests.conftest` imports; `workers/conftest.py` auto-applies to the
whole subtree, nothing to re-export).

**3c. `build_proxy` fake branch — mechanisms per shape, declared in the spec
(call sites verified).** Loader patching first (`monkeypatch.setattr(
worker_module, "<bare loader name>", fake_loader)` — bare names verified:
`load_pipeline_as_needed` (flux2/krea2/h3 flash),
`load_models_as_needed` (vision flash), `shared_load_models` /
`shared_load_pipeline` alias form (modal)); then the provider bypass,
because direct construction + call fails on both providers:
- Flash cls/pre (incl. vision): `wrapper._class_type` (pinned
  runpod-flash==1.7.0) → manual `__new__` + `__init__` (patched loader) →
  call the same method-body code. The decorated `RemoteClassWrapper`
  dispatches methods remotely — never awaited in fake.
- Modal cls (incl. vision): `_get_user_cls()` +
  `PartialFunction._get_raw_f()` (pinned modal==1.5.5) → hand-built instance
  (`__new__` + `storage` and `pipe_attrs` from the fake builder, mirroring
  `__init__` + `load()`) → call the same method-body code. Direct calls
  raise `TypeError` and `.local()` runs `@modal.enter()` (boots real models
  — forbidden in fake). Both bypasses are fake-path-only with version
  asserts; they break loudly on SDK upgrade, which is the desired tripwire.
- Beam tq/eq: NO monkeypatch — `generate`/`analyze` consume
  `context.on_start_value`; proxy passes
  `FakeCtx(on_start_value=fake_builder())`.
- Comfy flash: post-construction `worker.endpoint = FakeEndpoint()` (async
  `runsync` → `{error:None, output:{images:[{data: b64mp4}]}}`;
  constructor's real `Endpoint(...)` is network-inert until called).
- Comfy beam: monkeypatch worker-module `requests.post` (→ canned
  `prompt_id`) + `requests.get` (URL contains `/history/` → canned outputs
  JSON, else canned mp4 bytes).
- Voice asgi (`beam_asgi`, `modal_asgi`): stub `models` only
  (`load_models`/`load_model` → canned dict / `StubTTS`); build the REAL app
  (`worker(ctx)` / `build_web_app(pipeline)`) with the REAL session logic;
  proxy exposes `generate(**kw)` hiding a `TestClient` websocket exchange
  (`send {type,session,audio}` → `receive_json()`). Live branch returns the
  same `generate` signature over the dev endpoint (Todo 5).

**3d. Fake builders (canned outputs only — no content inspection).**
- flux2/krea2/h3 standard: canned artifact payloads (`FakePipe.__call__`
  → red PIL / canned video stub ≥256B); failure rule §2c applies first.
- h3 fl2va/ref2va: fake writer writes the canned stub to `output_path`
  (`run_*` take `pipe`/`write_video_audio` as DI args — no loader patching
  inside `run_*`, ever).
- vision: `_fake_run_analyze(model, processor, prompt, req)` ignores the
  image — sentinel `"failure"` raises, anything else returns the canned
  `SmallVisionOutput(classification="landscape_0p", subjects=[...],
  description="canned")`. Readers (`decode_image`, `read_*`) stay REAL
  (PIL/numpy, CPU-safe); tests use ref-free inputs so readers are exercised,
  not mocked.
- voice: `CANNED_QWEN_MODELS` (`StubTTS` with canned PCM, stub
  STT/LLM/VAD with fixed outputs), `StubPipeline` for modal chat. Contract
  check is against `voice/contracts/realtime_voice_*.json` output event
  enums.

**3e. Rewrite all ~20 request/response test files (flux2, krea2, h3,
vision).** Import the spec (`from workers.<model>.testing import <SPEC> as
SPEC`); fixtures resolve provider/kind from it (no per-file fixture
choice); `worker = platform.create_worker(storage=storage)`;
`result = runner.run(worker, <same kwargs as today>)`; keep every existing
assertion byte-identical except the vision failure-test sentinel swap (§2c).
No test logic changes — same inputs, same asserts, new plumbing. Bodies never
mention sync/async.

**3f. Write new voice tests (`workers/voice/tests/`, empty today).** Same
SPEC-import + triple pattern; websocket hidden inside `generate`:
- `test_session_created`: `runner.run(worker, type="session.update",
  session={})` → `evt["type"] in ("session.created", "session.updated",
  "error")` per `realtime_voice_*.json`.
- `test_failure`: `runner.run(worker, type="failure")` →
  `RuntimeError("inference failed")`.
- `test_chatterbox_speech` / `test_chatterbox_voices`: same triple against
  the chatterbox specs (REST surface via the proxy's `generate`).
Specs for openvoice/chatterbox/qwen beam asgi + modal chat. Fixtures follow
the interaction protocol, not the product: all realtime-WebSocket workers
share the voice ws fixture however different the products are; product
differences live in the spec + fake builder only. Qwen-beam's fake stubs
its external `build_app` boundary behind the same `generate()` signature —
it proves protocol/contract shape (no in-project session logic exists to
run), which is the honest scope.

**Verify (done-gate):** `pytest workers/ --target fake` fully green;
`pytest --collect-only` shows 0 import errors and every test file imports its
`SPEC`. Provider-bypass outcomes (recorded, verified at execution):
Modal direct local calls raise `TypeError: 'Function' object is not
callable` and `.local()` runs `@modal.enter()` (boots real models —
forbidden in fake), so modal_cls fakes reach the same method body via
`_get_user_cls()` + `PartialFunction._get_raw_f()` (pinned modal==1.5.5).
Flash `@Endpoint` wraps classes in `RemoteClassWrapper` (remote dispatch),
so flash fakes use `wrapper._class_type` (pinned runpod-flash==1.7.0).
Both are fake-path-only with version asserts; they break loudly on SDK
upgrade, which is the desired tripwire.

## Todo 4 — Remote shipping

- **Modal (mandatory — Modal 1.0 killed automount, verified):** insert
  `.add_local_python_source("workers.services", "workers.<model>")` into
  all 6 Modal `Image` chains (flux2, krea2, h3 fl2va, h3 ref2va, vision,
  voice chat),
  anchored after `.pip_install(...)`, before `.env(...)` /
  `.run_function(...)`. Deploy from repo root so names resolve.
- **Flash:** code change none (transitive auto-bundling covers siblings,
  docs-verified); **standardize on `flash deploy`** (resolves against whole
  project dir; ad-hoc runs treat parent-dir absolute imports as external).
  Parent-dir runtime imports don't exist (`services.*` is
  `TYPE_CHECKING`-only) — noted, not assumed.
- **Beam:** code change none for request/response (workspace snapshot,
  `.beamignore` evidence); Beam asgi voice workers ship the same way —
  assert `workers/` never enters `.beamignore`.
- **Ignore audit once:** `.gitignore` (Flash `build` fails loudly on
  excluded-but-imported modules — free tripwire, keep it that way) +
  `.beamignore`. Verified today: neither excludes `workers/`,
  `generate_*`, `services` — re-confirm post-move.
- **GPU-free verification:** `flash build` per model dir (free, fails on
  resolution errors); Modal CPU probe (5-line `modal run` on the touched
  image importing the same modules — resolves on CPU ⇒ resolves on GPU);
  one Beam dev probe per model (incl. one voice asgi).

## Todo 5 — Real bodies (end the theater)

- `Real*Platform.deploy()/undeploy()` = provider CLI commands
  (flash/beam/modal); fakes stay no-op. (Today all six are literally
  `pass` — verified.)
- Real runner request logic per provider × sync/async per verified
  mechanics: Flash `ep.run()` → `job.id` → `job.status()` loop →
  `job.output` (`runpod_flash/endpoint.py:744`); Modal `fn.spawn()` →
  `function_call_id` → `fc.get()` (`modal/_functions.py:2035`); Beam
  `client.submit()` → `Task.id` → `task.status()`/`is_complete()` →
  `result()` (`beta9/client/task.py:50`). Asyncio bridging (`asyncio.run` +
  ThreadPoolExecutor fallback, same trick the comfy flash workers use) for
  Flash/Modal SDKs; Beam stays sync (`requests`-based beta9 client).
  Statuses normalized to the 3-string contract; payload =
  spec `input_model(**kw).model_dump()`.
- Voice live: same `generate(**kw)` signature over the deployed dev
  endpoint (websocket for realtime workers, HTTP for chatterbox TTS);
  `live_endpoint` values filled into each voice spec.
- **Endpoint identity:** per-model `testing.py` constants
  (`FLASH_ENDPOINT`, `MODAL_APP`, `BEAM_SLUG`) — values read off decorator
  args at execution (e.g. `@Endpoint(name="flux2-klein9b-worker")`).
- `RealR2Storage` constructed inside the remote worker process, never
  passed from the test (boto3 clients don't serialize).
- **Verify (done-gate — fake-only):** `pytest workers/ --target fake` stays
  green (real bodies must not alter the fake path); `compileall` clean;
  `pytest --collect-only` shows the live specs resolving with
  `live_endpoint` filled and no `None` remaining; real-body code reviewed
  against the verified SDK mechanics cited above. Live execution itself is
  owner-run, outside this plan.

## Todo 6 — Hardening

- New `workers/tests/` (NO `__init__.py` — same collision lesson):
  `test_ceremony.py` (import every worker module; assert per-provider
  decorator params — non-empty gpu, image tags present, timeouts — required
  env keys; request/response `contracts/*.json` required-keys+title ↔ shared
  `Output` model equality over the mapping table; voice
  `contracts/realtime_voice_*.json` asserted separately against the output
  event-type enums),
  `test_marker_coverage.py` — deleted with the registry; a missing `SPEC`
  import fails at collection, so there is nothing to check.
- `.github/CODEOWNERS` (new — repo has none) covering
  fake/factory/harness paths; SDK pins from Todo 1e ("identical to
  provider" is meaningless against a moving target). No live/scheduled
  test workflow is created — the fake-only rule forbids it; live runs are
  owner-operated, not checked in.
- **Verify (done-gate):** `pytest workers/ --target fake` green including
  `workers/tests/`.

## Todo 3-pre — Voice import fix (precondition for Todo 3f)

Beam voice workers import `handlers`/`realtime` model packages that don't
exist in the repo (verified by repo-wide search): openvoice imported them at
top level (`handlers.voice_converter`, `realtime.audio/protocol/vad`),
chatterbox imported `handlers.chatterbox_tts` at top level; the qwen
worker's identical imports were already function-deferred. Resolution (no
in-project equivalents exist to vendor — `proxy/src/handlers` is unrelated
TS code): all three beam workers now defer those imports to loader/request
scope (qwen pattern), so every voice module imports cleanly and the fake
harness stubs at the loader/app boundary. The model packages remain
owner-supplied at deploy time (Beam ships the worker directory); remote boot
is owner-verified. Todo 3f's fake-green gate needs this — voice tests can't
collect without it.
**Verify (done-gate):** `python -m compileall workers/voice/` clean AND every
voice worker module imports locally with no `ModuleNotFoundError`. Todo 3
does not start until this gate passes.

## Todo 7 — Closed: no voice-core extraction (owner ruling)

Owner ruling: qwen-beam and modal-chat are DIFFERENT products. Fixtures
follow the interaction protocol, not the product — sharing one ws fixture
is correct, sharing implementation would couple things that change
independently. No `chat_core.py`, no `audio_util.py`, no worker rewrites.
Openvoice-converter and chatterbox-TTS stay untouched (separate products —
conversion-only and REST-only). This todo is documentation of the
divergence, not work.

## Execution order

1 → 2 → 3-pre (voice imports resolve; blocks Todo 3) → 3 (fake-green
harness, incl. new voice tests) → 4 (remotes actually resolve) → 5 (live
stops being theater) → 6 (lock it in). Todo 7 is closed (see above). Each
todo's Verify block is its done-gate; no todo starts until the previous
gate passes.
