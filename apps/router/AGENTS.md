# Router App

Stateless router routing across worker implementations of a defined contract.

**Whitelabel**:

- Targets: multiple, matching naming pattern `router-{worker name}`
- Project Deps: `{worker name}`'s `dev` and `deploy` targets

**Inputs**:

- Contract: `packages/contracts/{worker name}/contract.json`

**Generated on build**:

- `{WORKER_NAME}_ROUTER_SECRET_AUTH_TOKEN`: env, for cross-project auth
- `generated/types.ts`: generated from `contract` json schema

**Output**:

- `{WORKER_NAME}_ROUTER_URL`
- `{WORKER_NAME}_ROUTER_SECRET_AUTH_TOKEN`

**Endpoints**:

- Endpoints: `POST /infer`, `GET /inquire`

<!--- Provider dispatch: read URLs from environment (`BEAM_URL`, `BEAM_TASK_API`, `FLASH_URL`, `FLASH_ENDPOINT`); contracts carry input/output schemas only-->

- Auth: auth header validated to match `{WORKER_NAME}_SECRET_AUTH_TOKEN`
- Task ID: `base64("provider:originalTaskId")` — beam: task UUID from `.put()`, flash: endpoint call ID
- Status enum: `PENDING | PROCESSING | COMPLETED | FAILED | CANCELLED`
- v1 picks beam, but selection function is separate for future expansion
- Code must be minimal, simple and stupid — no magic, no `any`, no ifs without `{}`, no semis

### Workflow

**Read before writing code**:

- `task-id.ts` — encode/decode with `btoa`/`atob`
- `pick-task-handler.ts` — v1 returns `'beam'`
- `router.ts` — itty-router endpoints
