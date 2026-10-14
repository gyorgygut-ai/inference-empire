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

## NX target: `router:router-flux2`, `router:router-krea2`

**executor**: `orchestrator:run-injected-command`
**command**: `npx tsx watch apps/router/src/serve.ts`
**inject**: `../../tools/wait-for-artifact.ts input ../../dist/worker-{model}/deploy/MODAL_WORKER_URL`, `.../BEAM_WORKER_URL`; generate+drop+inject `SECRET_AUTH_TOKEN` via `../../tools/generate-auth-token.ts` + `artifact: dist/router-{model}/dev/SECRET_AUTH_TOKEN` in same target (no separate `generate-auth-token` target)
**artifact**: `dist/router-{model}/dev/PORT` (`PORT` only, no `ROUTER_URL` on dev: `echo "4201"` / `echo "4202"`)

**target:generate-api**:

- **executor**: `nx:run-commands` (stays, not orchestrator)
- **input: api**: `packages/contracts/api-task-queue.json`
- **input: worker**: `packages/contracts/{model}/inference.json`
- **output**: `dist/router-{model}/{dev|deploy}/api.json`

**target:generate-ts**:

- **executor**: `nx:run-commands` (stays, not orchestrator)
- **input**: `dist/router-{model}/{dev|deploy}/api.json`
- **output**: `./generated/api-{model}.ts` (per-model: `api-flux2.ts`, `api-krea2.ts`; `router.ts` imports both, `body` typed as union)

## NX target: `router:router-flux2-deploy`, `router:router-krea2-deploy`

**executor**: `orchestrator:run-command-with-artifact`
**command**: `tsx tools/deploy-vercel.ts router router-{model} router-{model} deploy ROUTER_URL --token $ROUTER_VERCEL_TOKEN --org $ROUTER_VERCEL_ORG_ID --project-id $ROUTER_VERCEL_PROJECT_ID`
**artifact**: `dist/router-{model}/deploy/ROUTER_URL` (deploy-vercel prints URL last line)
**depends**: `router-{model}-generate-api`, `router-{model}-generate-ts`, `router-{model}-generate-auth-token-deploy`

**target:generate-auth-token-deploy**:

- **executor**: `orchestrator:run-command-with-artifact`
- **command**: `tsx tools/generate-auth-token.ts`
- **artifact**: `dist/router-{model}/deploy/SECRET_AUTH_TOKEN`
- NOTE: `SECRET_AUTH_TOKEN` must also be set as Vercel env on the router projects (out of nx scope)
