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

- **depends**: `worker-flux2:dev-modal`
- **command**: `tsx watch`
- **artifact**: `ROUTER_URL` to `@dist/router-flux2/dev.env`
- **envFile**: `@dist/worker-flux2/dev.env` - readonly

**:deploy**:

- **depends**: `worker-flux2:deploy-modal`
- **command**: `@tools/deploy-vercel`
- **artifact**: `ROUTER_URL` to `@dist/router-flux2/deploy.env`
- **envFile**: `@dist/worker-flux2/deploy.env` - readonly

**target:generate-api**:

- **command**: `run-commands` `./scripts/generate-api`
- **input: api**: `@packages/contracts/api-task-queue.json`
- **input: worker**: `@packages/contracts/flux2/inference.json`
- **output + artifact**: `@dist/router-flux2/api-{dev|deploy}.json`

**target:generate-ts**:

- **command**: `run-commands` `./scripts/generate-ts`
- **input: api**: `@dist/router-flux2/api-{dev|deploy}.json`
- **output**: `./generated/api.ts`

**target:generate-auth-token**:

- **command**: `run-commands` `@tools/orchestraiton/generate-auth-token`
- **output**: `SECRET_AUTH_TOKEN` to `@dist/router-flux2/{dev|deploy}.env`

---

## NX target: `router-krea2:(dev|deploy)`

**:dev**:

- **depends**: `worker-krea2:dev-modal`
- **command**: `tsx watch`
- **envFile**: `@dist/worker-krea2/dev.env`
- **artifact**: `ROUTER_URL` to `@dist/router-krea2/dev.env`

**:deploy**:

- **depends**: `worker-krea2:deploy-modal`
- **command**: `@tools/deploy-vercel`
- **envFile**: `@dist/worker-krea2/deploy.env`
- **artifact**: `ROUTER_URL` to `@dist/router-krea2/deploy.env`

**target:generate-api**:

- **command**: `run-commands` `./scripts/generate-api`
- **input: api**: `@packages/contracts/api-task-queue.json`
- **input: worker**: `@packages/contracts/krea2/inference.json`
- **output + artifact**: `@dist/router-krea2/api-{dev|deploy}.json`

**target:generate-ts**:

- **command**: `run-commands` `./scripts/generate-ts`
- **input: api**: `@dist/router-krea2/api-{dev|deploy}.json`
- **output**: `./generated/api.ts`

**target:generate-auth-token**:

- **command**: `run-commands` `@tools/orchestraiton/generate-auth-token`
- **output**: `SECRET_AUTH_TOKEN` to `@dist/router-krea2/{dev|deploy}.env`
