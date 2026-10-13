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

## NX target: `router-flux2:(dev|deploy)`

**:dev**:

- **depends**: `worker-flux2:deploy-modal` + `worker-flux2:deploy-beam`
- **command**: `tsx watch`
- **artifact**: `@dist/router-flux2/dev/ROUTER_URL`
- **env vars**:
  - any local env handled by nx
  - source `@dist/worker-flux2/dev/*_WORKER_URL`

**:deploy**:

- **depends**: `worker-flux2:deploy-modal`
- **command**: `@tools/deploy-vercel`
- **artifact**: `@dist/router-flux2/deploy/ROUTER_URL`
- **env vars**:
  - any local env handled by nx
  - source `@dist/worker-flux2/deploy/*_WORKER_URL`

**target:generate-api**:

- **command**: `run-commands` `./scripts/generate-api`
- **input: api**: `@packages/contracts/api-task-queue.json`
- **input: worker**: `@packages/contracts/flux2/inference.json`
- **output + artifact**: `@dist/router-flux2/{dev|deploy}/api.json`

**target:generate-ts**:

- **command**: `run-commands` `./scripts/generate-ts`
- **input: api**: `@dist/router-flux2/{dev|deploy}/api.json`
- **output**: `./generated/api.ts`

**target:generate-auth-token**:

- **command**: `run-commands` `@tools/orchestration/generate-auth-token`
- **output**: `@dist/router-flux2/{dev|deploy}/ROUTER_SECRET_AUTH_TOKEN`
- **artifact**: `@dist/router-flux2/{dev|deploy}/ROUTER_SECRET_AUTH_TOKEN`

---

## NX target: `router-krea2:(dev|deploy)`

**:dev**:

- **depends**: `worker-krea2:deploy-beam`
- **command**: `tsx watch`
- **artifact**: `@dist/router-krea2/dev/ROUTER_URL`
- **env vars**:
  - any local env handled by nx
  - source `@dist/worker-krea2/dev/*_WORKER_URL`

**:deploy**:

- **depends**: `worker-krea2:deploy-modal`
- **command**: `@tools/deploy-vercel`
- **artifact**: `@dist/router-krea2/deploy/ROUTER_URL`
- **env vars**:
  - any local env handled by nx
  - source `@dist/worker-krea2/deploy/*_WORKER_URL`

**target:generate-api**:

- **command**: `run-commands` `./scripts/generate-api`
- **input: api**: `@packages/contracts/api-task-queue.json`
- **input: worker**: `@packages/contracts/krea2/inference.json`
- **output + artifact**: `@dist/router-krea2/{dev|deploy}/api.json`

**target:generate-ts**:

- **command**: `run-commands` `./scripts/generate-ts`
- **input: api**: `@dist/router-krea2/{dev|deploy}/api.json`
- **output**: `./generated/api.ts`

**target:generate-auth-token**:

- **command**: `run-commands` `@tools/orchestration/generate-auth-token`
- **output**: `@dist/router-krea2/{dev|deploy}/ROUTER_SECRET_AUTH_TOKEN`
- **artifact**: `@dist/router-krea2/{dev|deploy}/ROUTER_SECRET_AUTH_TOKEN`
