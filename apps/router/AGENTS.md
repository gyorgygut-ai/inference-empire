# Router App

Stateless router routing across worker implementations of a contract.

**Endpoints**:

- POST `/q`; auth against `env.SECRET_AUTH_TOKEN`
- GET `/sup`; auth against `env.SECRET_AUTH_TOKEN`

**Business Logic**:

- Status: `PENDING | PROCESSING | COMPLETED | FAILED | CANCELLED`
- Task ID: `base64("provider:originalTaskId")`
- Pick: `modal` (hardcoded, temporary)

---

## Per-model builds

One `router` codebase, built once per model. `createRouter<TAddRequest, TAddResponse, TSupResponse>()` (`src/router.ts`) is model-agnostic; each entry (`src/models/{model}.ts`) binds the three types from its own `generated/api-{model}.ts`; `loadModel()` (`src/models/index.ts`) selects the entry from `ROUTER_MODEL`. A router build imports only its own contract.

## NX targets (task-first, `{model}` suffix)

**env-dev-{model}**:

- **executor**: `nx:run-commands`, `cache: false`
- **command**: `tsx tools/router-env.ts {model} dev`
- **reads**: `FLUX2_ROUTER_PORT` / `KREA2_ROUTER_PORT` from `apps/router/.env.local`, validated by `routerPortsSchema` (`env.schema.ts`)
- **writes**: `dist/router-{model}/dev/{PORT,ROUTER_URL,SECRET_AUTH_TOKEN}` — `PORT` = that model's port, `ROUTER_URL` = `http://localhost:$PORT`

**env-deploy-{model}**:

- **executor**: `nx:run-commands`, `cache: false`
- **command**: `tsx tools/router-env.ts {model} deploy`
- **writes**: `dist/router-{model}/deploy/SECRET_AUTH_TOKEN`

**generate-api-{model}**:

- **executor**: `nx:run-commands`, `cache: true`
- **input: api**: `packages/contracts/api-task-queue.json`
- **input: worker**: `packages/contracts/{model}/inference.json`
- **output**: `dist/router-{model}/api.json`

**generate-ts-{model}**:

- **executor**: `nx:run-commands`, `cache: true`
- **input**: `dist/router-{model}/api.json`
- **output**: `./generated/api-{model}.ts`

**dev-{model}**:

- **executor**: `nx:run-commands`, `cache: false`, `continuous: true`
- **command**: `ROUTER_MODEL={model} npx tsx tools/export-artifacts.ts dist/worker-{model}/deploy dist/router-{model}/dev -- npx tsx watch apps/router/src/serve.ts`
- **readyWhen**: `listening on` (`[router-{model}] listening on http://127.0.0.1:{$PORT} modal=… beam=… flash=…`)
- **depends**: `worker-{model}:deploy-modal` (flux2 also `deploy-beam`), `env-dev-{model}`, `generate-ts-{model}`

**deploy-{model}**:

- **executor**: `nx:run-commands`, `cache: false`
- **command**: `ROUTER_MODEL={model} npx tsx tools/export-artifacts.ts dist/worker-{model}/deploy dist/router-{model}/deploy -- npx tsx tools/deploy-vercel.ts router --token $..._TOKEN --org $..._ORG_ID --project-id $..._PROJECT_ID > dist/router-{model}/deploy/ROUTER_URL`
- **depends**: `worker-{model}:deploy-modal`, `worker-{model}:deploy-beam`, `env-deploy-{model}`, `generate-ts-{model}`

**Env**: `PORT`/`ROUTER_MODEL` are validated in `env.schema.ts`; `serve.ts` reads `PORT` from env with no fallback. `ROUTER_MODEL` is a per-target command constant, never an artifact. No `nx:run-commands` target-level `env:` is used anywhere. The boot line prints the loaded `PORT` and the non-secret worker URLs (`modal=`, `beam=`, `flash=`) so the runtime's held values are directly comparable; `SECRET_AUTH_TOKEN` is never logged. Runtime env (`SECRET_AUTH_TOKEN`, `ROUTER_URL`, `ROUTER_MODEL`, `MODAL/BEAM/FLASH_WORKER_URL`) is forwarded centrally by `deploy-vercel.ts` from `process.env`; no `-e` flags in `project.json`.
