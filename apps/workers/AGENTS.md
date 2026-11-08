# GPU Workers

## SPECS

**Artifacts**:

- **Problem**: Callers need generated media without receiving large media payloads inline.
- **Acceptance**:
  - Upload media to R2 and return a `presigned_url`.
  - Return `text`, `json`, `realtime`, and `audio` data directly.
- **Outcome**: Media is available by URL; direct-response data stays inline.

**Worker configuration**:

- **Problem**: Workers need fast starts and controlled idle costs.
- **Acceptance**:
  - **Flash**: use `flashboot=True`.
  - **Modal**: use a model cache.
  - **Beam**: use the `./hf-cache` volume.
  - Use at most one worker, scale to zero, and use short idle timeouts.
  - Download models lazily and cache them on first request.
  - Name the function or endpoint `generate`.
- **Outcome**: Workers reuse model assets and scale down when idle.

**Worker structure**:

- **Problem**: Platform wrappers, business logic, and generated contracts need clear boundaries.
- **Acceptance**:
  - Keep each thin platform wrapper at `{projectRoot}/worker_{model}_{platform}.py`.
  - Keep shared business logic at `{projectRoot}/shared/worker_{model}.py` and use it from wrappers.
  - `prebuild` generates Pydantic contracts into ignored `{projectRoot}/dist/`.
  - Generate `Input`/`Output` types from `packages/schemas/workers/*.schema.json`; never hand-edit generated contracts.
  - Keep artifact uploads and validation under `{projectRoot}/shared/**/*.py`; keep them self-contained.
  - Local-only fake workers may use a thin platform wrapper and shared stub logic under `{projectRoot}/fakes/`; keep fake code self-contained, CPU-only, and outside deploy targets.
- **Outcome**: Each worker separates platform code, shared logic, and generated contracts.

## DEPLOY

`worker-{family}:deploy`:

- Run the platform deploy command directly: `{modal|beam|flash|cerebrium} deploy`.
- Expose `deploy` as the public target.
- Use `deploy-{platform}` only as an internal edge when a worker has multiple platforms.
- Deploy from `{projectRoot}` with no extra files.
- Deploy only to Modal and Beam for now; maintain other platforms without deploying them.

## NON-NEGOTIABLES

- Avoid imports from outside `{projectRoot}`.
- Remove dead code and shortcuts; always lint.
- Queue tasks and return a task ID where possible.
- Use `worker-{family}` consistently for the Nx project, deployed app, Python distribution, and cache volume.
- Push environment variables idempotently during deploy; do not set them manually.
- Root workspace credentials use the `SECRET_*` prefix. `project.json` maps them to each worker's prefixless application environment names. Platform credentials such as `SECRET_HUGGINGFACE_TOKEN` retain their documented runtime names.
- Authenticate every Hugging Face Hub request with `SECRET_HUGGINGFACE_TOKEN`. Pass the token directly to Hub APIs and initialize Hub authentication before libraries perform internal downloads.
- Keep workspace credential names static and descriptive in `.env`; encrypt sensitive values with dotenvx.
- Never put container-only `SECRET_*` names in `packages/schemas/env/*`.

## TESTING

- **Proof**: each test proves a stated requirement; no filler.
- **Targets**: use `test-unit` and `test-acceptance`; omit model or API suffixes from target names.
- **Coverage**: cover valid and invalid input, expected output, and any artifact required by the worker’s contract.
- **Side effects**: avoid mocks; use real stubs and dependency injection.
- **E2E**: one successful end-to-end case per worker, with no stubs. Assert contract output and any required artifact.

## VERIFICATION

- Lint after changes; work is not finished until lint passes.
- Deploy only finished, verified, clean code.
- Logs must identify deploy and runtime errors.
apps/workers/stt/AGENTS.md
