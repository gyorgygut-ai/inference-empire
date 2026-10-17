# Router App

Stateless router routing across worker implementations of a schema.

**Endpoints**:

- POST `/q`; auth against `env.ROUTER_AUTH_TOKEN`
- GET `/sup`; auth against `env.ROUTER_AUTH_TOKEN`

**Business Logic**:

- Status: `PENDING | PROCESSING | COMPLETED | FAILED | CANCELLED`
- Task ID: `base64("provider:originalTaskId")`
- Pick: `modal` (hardcoded, temporary)

---

## Source layout

- `src/router.ts`: routing behaviour, `createRouter`
- `src/serve.ts`: dev transport; prints `listening on http://127.0.0.1:{env.PORT}` on stdout
- `api/[[...route]].ts`: deployed entry; `createRouter()`
- `src/providers/`: worker providers

---

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

- **deps**: `{ target: "worker-flux2:deploy-modal", options: "forward" }`, `{ target: "generate-*", options: "forward" }`, `dev-flux2-generate-*`, `schemas:generate-flux2-*`
- **executor**: `nx/run-commands`
- **command**: `PORT=$(node -p \"new URL(process.env.FLUX2_ROUTER_URL).port\")  npm run dev`
- **envFile**: `{workspaceRoot}/dist/flux2/dev.env`

**router:dev-krea2**:

- **deps**: `{ target: "worker-krea2:deploy-modal", options: "forward" }`, `{ target: "generate-*", options: "forward" }`, `dev-krea2-generate-*`, `schemas:generate-krea2-*`
- **executor**: `orchestrator/run-command`
- **command**: `PORT=$(node -p \"new URL(process.env.KREA2_ROUTER_URL).port\") npm run dev`
- **envFile**: `{workspaceRoot}/dist/krea2/dev.env`

**router:deploy-flux2**:

- **deps**: `{ target: "worker-flux2:deploy-modal", options: "forward" }`, `{ target: "generate-*", options: "forward" }`, `schemas:generate-flux2-*`
- **executor**: `orchestrator/run-command`
- **command**: `tools/deploy-vercel.ts` `--token $FLUX2_ROUTER_VERCEL_TOKEN --org $FLUX2_ROUTER_VERCEL_ORG_ID --project-id $FLUX2_ROUTER_VERCEL_PROJECT_ID`
- **envKey**: `ROUTER_URL`
- **envFile**: `{workspaceRoot}/dist/flux2/deploy.env`
- **output**: command must output deployed url to stdout

**router:deploy-krea2**:

- **deps**: `{ target: "worker-krea2:deploy-modal", options: "forward" }`, `{ target: "generate-*", options: "forward" }`, `schemas:generate-krea2-*`
- **executor**: `orchestrator/run-command`
- **command**: `tools/deploy-vercel.ts` `--token $KREA2_ROUTER_VERCEL_TOKEN --org $KREA2_ROUTER_VERCEL_ORG_ID --project-id $KREA2_ROUTER_VERCEL_PROJECT_ID`
- **envKey**: `ROUTER_URL`
- **envFile**: `{workspaceRoot}/dist/krea2/deploy.env`
- **output**: command must output deployed url to stdout
