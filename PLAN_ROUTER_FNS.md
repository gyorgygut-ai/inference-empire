# Plan: Router Functions Implementation — `apps/functions`

**Goal**: Adapt legacy router code from `apps/router_legacy/` to match the `apps/functions` spec, implementing the Netlify Functions entry points, shared router, strategies, and services per the AGENTS.md contract.

---

## Gaps in `apps/functions` (inner code, package.json, src/)

### 1. `apps/functions/package.json` — missing runtime dependencies
- **Current**: private package with only `"build": "echo 'no build needed'"`
- **Required**: add `@netlify/functions`, `itty-router`, `zod` as dependencies
- **Why**: router handler uses `Handler` type from `@netlify/functions`, `itty-router` for routing, `zod` for schema validation

### 2. `apps/functions/src/` — shared router + strategies + services directory missing
- **Current**: `src/main.ts` only has `console.log('Hello World')`
- **Required**: create `src/_shared/` with:
  - `_shared/router.ts` — itty-router entry, auth middleware, POST `/q` and GET `/sup` endpoints, delegates to strategies
  - `_shared/strategies/strategy-beam.ts` — provider config resolving `WORKER_RESOLVED_BEAM_URL`, task-id encoding/decoding (`base64("provider:originalTaskId")`), push/fetch to task queue
  - `_shared/strategies/strategy-modal.ts` — same for modal worker
  - `_shared/strategies/strategy-flash.ts` — same for flash worker
  - `_shared/services/pick-strategy.ts` — returns `"beam"` (hardcoded temporary, per spec)
  - `_shared/services/create-strategy.ts` — creates strategy instance from name

### 3. `apps/functions/functions/router/router.ts` — placeholder only
- **Current**: returns static "flux2"/"krea2" strings, no auth, no task queue
- **Required**: replace with real handler that:
  - Authenticates against `ROUTER_GENERATED_AUTH_TOKEN` from contract env
  - POST `/q`: parse input against loaded model schema (flux2/krea2), call `pick-strategy`, create strategy, push to queue, return `{ task_id: "base64:..." }`
  - GET `/sup`: decode task_id, fetch status from worker, validate output against schema, return `{ status: "PENDING"|"PROCESSING"|"COMPLETED"|"FAILED"|"CANCELLED", output: {...} }`
  - 404 for unknown paths

### 4. `apps/functions/netlify.toml` — redirects need per-model entry functions
- **Current**: both `/flux2/*` and `/krea2/*` redirect to `/.netlify/functions/router` (single handler)
- **Required**: split redirects to separate functions per model:
  ```
  [[redirects]]
  from = "/flux2/*"
  to = "/.netlify/functions/router_flux2"
  status = 200

  [[redirects]]
  from = "/krea2/*"
  to = "/.netlify/functions/router_krea2"
  status = 200
  ```

---

## Adaptation from Legacy Router (`apps/router_legacy/`)

Map legacy source → functions spec:

| Legacy Path | Functions Path | Notes |
|---|---|---|
| `apps/router_legacy/src/router.ts` | `apps/functions/src/_shared/router.ts` | Adapt: add auth check for `ROUTER_GENERATED_AUTH_TOKEN` (from WorkerServiceContract), keep POST `/q` / GET `/sup`, keep 404 fallback |
| `apps/router_legacy/src/task-queue-api.ts` | `apps/functions/src/_shared/task-queue-api.ts` (reuse type) | Status union type: `PENDING | PROCESSING | COMPLETED | FAILED | CANCELLED` |
| `apps/router_legacy/src/providers/provider-beam.ts` | `apps/functions/src/_shared/strategies/strategy-beam.ts` | Adapt: resolveConfig reads `WORKER_RESOLVED_BEAM_URL` from contract env; encodeTaskId = `btoa(\`beam:${originalTaskId}\`)`; push/fetch via fetch to `${url}/queues/default` |
| Same for modal/flash → `strategy-modal.ts` / `strategy-flash.ts` | Same pattern | |
| `apps/router_legacy/src/pick-task-handler.ts` | `apps/functions/src/_shared/services/pick-strategy.ts` | Change return from `"modal"` → `"beam"` (hardcoded temporary per spec) |
| `apps/router_legacy/src/schema.flux2.ts` / `schema.krea2.ts` | `packages/schemas/flux2/schema.ts` / `packages/schemas/krea2/schema.ts` | Generated via `tools/generate-zod-from-json.ts`; entry files load generated `schema.ts` |
| `apps/router_legacy/src/env.schema.ts` | `packages/contracts/worker-service/worker-service.contract.ts` + contract env files | Auth token loaded from `TaskQueueServiceContract.ROUTER_GENERATED_AUTH_TOKEN` written by `generate-auth-token` target |

---

## Netlify Function Entry Files (new)

Create per-model files:

### `apps/functions/functions/router_flux2.ts`
```ts
import type { Handler } from "@netlify/functions"
import { createRouter } from "../_shared/router"
import { flux2Schema } from "@inference/schemas/flux2/schema"

export const handler: Handler = createRouter(flux2Schema)
```

### `apps/functions/functions/router_krea2.ts`
```ts
import type { Handler } from "@netlify/functions"
import { createRouter } from "../_shared/router"
import { krea2Schema } from "@inference/schemas/krea2/schema"

export const handler: Handler = createRouter(krea2Schema)
```

Each entry file loads its model's generated zod schema and passes it to the shared router factory.

---

## Orchestrator Chain (functions targets)

Per AGENTS.md spec, add these targets to `apps/functions/project.json` (inner code, not nx config):

1. **`generate-auth-token`**
   - executor: `orchestrator:run-command`
   - command: `tools/generate-auth-token.ts`
   - fulfills: `{contract: "task-queue-service", contractKey: "ROUTER_GENERATED_AUTH_TOKEN"}`
   - writes auth token to contract env file

2. **`prebuild`**
   - dependsOn: `["^prebuild", "generate-*"]`
   - builds schema.ts from packages/schemas

3. **`predev`**
   - dependsOn: `prebuild`

4. **`dev-flux2`**
   - executor: `orchestrator:run-command` (or `nx:run-commands`)
   - command: `tools/serve-netlify-functions.ts`
   - needs: flux2 WorkerServiceContract + TaskQueueServiceContract
   - fulfills: TaskQueueServiceContract.ROUTER_RESOLVED_URL
   - envFile: `dist/flux2/dev.env`
   - waits for router READY on http://127.0.0.1:5050

5. **`deploy-flux2`**
   - executor: `orchestrator:run-command`
   - command: `netlify deploy`
   - needs: flux2 WorkerServiceContract + TaskQueueServiceContract
   - fulfills: TaskQueueServiceContract.ROUTER_RESOLVED_URL
   - writes deployed URL to `dist/flux2/deploy.env`

6. **`dev-krea2`** / **`deploy-krea2`** — same pattern with `krea2`

---

## Dependency Chain Verification

```
deploy-flux2
  → dependsOn build
  → needs: flux2 WorkerServiceContract (WORKER_RESOLVED_BEAM_URL in workers.env)
  → needs: flux2 TaskQueueServiceContract (ROUTER_RESOLVED_URL + ROUTER_GENERATED_AUTH_TOKEN in dev.env)
  → fulfills: TaskQueueServiceContract.ROUTER_RESOLVED_URL

dev-flux2
  → dependsOn predev + prebuild + generate-auth-token
  → needs: same contracts
  → fulfills: ROUTER_RESOLVED_URL
  → router listens on http://127.0.0.1:5050
  → face-value:dev dependsOn functions:dev-flux2 + needs TaskQueueServiceContract
```

---

## Success Criteria (verifiable with `netlify dev`)

- `POST /q` with valid auth → `200 { task_id: "base64:..." }`
- `GET /sup?id=...` → `200 { status: "PENDING"|... }`
- Auth fails without/with wrong token → `401`
- Schema validation via zod catches bad input bodies
- `ROUTER_GENERATED_AUTH_TOKEN` written by `generate-auth-token` contract target
- Workers write `WORKER_URL_*` to `dist/deploy/flux2/workers.env` via deploy targets
- `face-value:dev` starts, connects to router at `ROUTER_RESOLVED_URL`, serves chat UI