# Router App

LEGACY: DO NOT TOUCH Stateless router routing across worker implementations of a schema.


**Endpoints**:

- POST `/q`; auth against `env.ROUTER_AUTH_TOKEN`
- GET `/sup`; auth against `env.ROUTER_AUTH_TOKEN`

**Env**:

- required: `ROUTER_AUTH_TOKEN`, `PORT` (supplied by the dev target; the deployed entry defaults it)
- optional: `MODAL_WORKER_URL`, `BEAM_WORKER_URL`, `FLASH_WORKER_URL`
- `ROUTER_URL` is a deploy artifact, not a router env

**Business Logic**:

- Status: `PENDING | PROCESSING | COMPLETED | FAILED | CANCELLED`
- Task ID: `base64("provider:originalTaskId")`
- Pick: `modal` (hardcoded, temporary)

---

## Source layout

- `src/router.ts`: routing behaviour, `createRouter`
- `src/schema.ts`: generated zod schema for `${ROUTER_MODEL:-flux2}` (gitignored, written by `predev` and the Vercel build)
- `src/serve.ts`: dev transport; prints `listening on http://127.0.0.1:{env.PORT}` on stdout
- `api/[[...route]].ts`: deployed entry; Vercel mounts it at `/api/*`, `vercel.json` rewrites `/q` and `/sup` onto it
- `src/providers/`: worker providers

---

## NX: `router:dev-flux2`

**Run**: `netlify dev`

**MUST DO before `dev-flux2`**:

  - **Workers** must be deployed: `workers-flux2:deploy-modal`, `workers-flux2:deploy-beam`
  - **Write** local server `ROUTER_URL` to `{workspaceRoot}/dist/deploy/flux2/router.env`
  - **Generate** flux2 api types to `{projectRoot}/dist/`
  - **Generate** new `ROUTER_AUTH_TOKEN` to `{workspaceRoot}/dist/deploy/flux2/router.env`

**Critical `envFile`**:

  - **WORKER_URL_MODAL**: `{workspaceRoot}/dist/deploy/flux2/workers.env`
  - **WORKER_URL_BEAM**: `{workspaceRoot}/dist/deploy/flux2/workers.env`

## NX: `router:deploy-flux2`

**Command**: `netlify deploy`

**MUST DO before `deploy-flux2`**:

  - **Workers** must be deployed: `workers-flux2:deploy-modal`, `workers-flux2:deploy-beam`
  - **Write** deployed `ROUTER_URL` to `{workspaceRoot}/dist/deploy/flux2/router.env`
  - **Generate** flux2 api types to `{projectRoot}/dist/`
  - **Generate** new `ROUTER_AUTH_TOKEN` to `{workspaceRoot}/dist/deploy/flux2/router.env`

**Critical `envFile`**:

  - **WORKER_URL_MODAL**: `{workspaceRoot}/dist/deploy/flux2/workers.env`
  - **WORKER_URL_BEAM**: `{workspaceRoot}/dist/deploy/flux2/workers.env`

## NX Targets

**Option Forwarding**:

- **problem**: deps in the chain must read and write the same `envFile`
- **outcome**: one `envFile` across the chain; no target bloat

**router:generate-auth-token**:

- **executor**: `orchestrator/run-command`
- **command**: `tools/generate-auth-token.ts`
- **envKey**: `ROUTER_AUTH_TOKEN`
- **output**: brand-new auth token to stdout

**router:dev-flux2**:

- **deps**: `{ projects: ["worker-flux2"], target: "deploy-modal", options: "forward" }`, `{ projects: ["worker-flux2"], target: "deploy-beam", options: "forward" }`, `{ target: "generate-*", options: "forward" }`, `dev-flux2-generate-*`, `schemas:generate-flux2-*`
- **executor**: `nx/run-commands`
- **command**: `PORT=$(node -p \"new URL(process.env.FLUX2_ROUTER_URL).port\")  npm run dev`
- **envFile**: `{workspaceRoot}/dist/flux2/dev.env`

**router:dev-krea2**:

- **deps**: `{ projects: ["worker-krea2"], target: "deploy-modal", options: "forward" }`, `{ target: "generate-*", options: "forward" }`, `dev-krea2-generate-*`, `schemas:generate-krea2-*`
- **executor**: `orchestrator/run-command`
- **command**: `PORT=$(node -p \"new URL(process.env.KREA2_ROUTER_URL).port\") npm run dev`
- **envFile**: `{workspaceRoot}/dist/krea2/dev.env`

**router:deploy-flux2**:

- **deps**: `{ projects: ["worker-flux2"], target: "deploy-modal", options: "forward" }`, `{ projects: ["worker-flux2"], target: "deploy-beam", options: "forward" }`, `{ target: "generate-*", options: "forward" }`, `schemas:generate-flux2-*`
- **executor**: `orchestrator/run-command`
- **command**: `tools/deploy-vercel.ts` `router` `from-root` `--token $FLUX2_ROUTER_VERCEL_TOKEN --org $FLUX2_ROUTER_VERCEL_ORG_ID --project-id $FLUX2_ROUTER_VERCEL_PROJECT_ID`
- **envKey**: `ROUTER_URL`
- **envFile**: `{workspaceRoot}/dist/flux2/deploy.env`
- **output**: command must output deployed url to stdout

**router:deploy-krea2**:

- **deps**: `{ projects: ["worker-krea2"], target: "deploy-modal", options: "forward" }`, `{ target: "generate-*", options: "forward" }`, `schemas:generate-krea2-*`
- **executor**: `orchestrator/run-command`
- **command**: `tools/deploy-vercel.ts` `krea2` `from-root` `--token $KREA2_ROUTER_VERCEL_TOKEN --org $KREA2_ROUTER_VERCEL_ORG_ID --project-id $KREA2_ROUTER_VERCEL_PROJECT_ID`
- **envKey**: `ROUTER_URL`
- **envFile**: `{workspaceRoot}/dist/krea2/deploy.env`
- **output**: command must output deployed url to stdout
