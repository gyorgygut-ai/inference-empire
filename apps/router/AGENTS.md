# Router App

Stateless router routing across worker implementations of a contract.

**NX Project**:

- Project `router`, `executor: nx:run-commands`, `defaultConfiguration: dev`, `cache: false`, `continuous: true`
- Targets `router-flux2`, `router-krea2`, each with `configurations: { dev: { command, envFile }, deploy: { command, envFile } }`
- Each serving target sets `dependsOn: [{ projects: [worker-{model}], target: deploy-modal, configuration: matched }, router-{worker}-env, router-{worker}-generate-api, router-{worker}-generate-ts]`

**target:router-{worker}-env**:

- **inputs**: worker artifact `dist/worker-{model}/deploy/deploy-modal.env`
- **outputs**: `dist/router/{dev|deploy}/router-{worker}.env`
- **command**: `TOKEN=$(tsx tools/orchestration/generate-auth-token.ts)` plus `tsx tools/orchestration/upsert-artifact.ts router {dev|deploy} router-{worker} APP_URL=... SECRET_AUTH_TOKEN=$TOKEN`

**target:generate-api**:

- **inputs**: `{workspaceRoot}/packages/contracts/{worker}/inference.json`, `{workspaceRoot}/packages/contracts/api-task-queue.json`
- **outputs**: `dist/{worker}_api.json`
- **cache**: true

**target:generate-ts**:

- **inputs**: `dist/{worker}_api.json`
- **outputs**: `generated/router_{worker}_api.ts`
- **dependsOn**: `router-{worker}-generate-api`
- **cache**: true

**Environment**:

- Loaded via `envFile: dist/router/{dev|deploy}/router-{worker}.env` in `configurations`, never via `process.argv` path
- `Env = { SECRET_AUTH_TOKEN }`
- `APP_URL` written by `router-{worker}-env` on `dev` plus `deploy`
- `SECRET_AUTH_TOKEN`: minted fresh by `router-{worker}-env` each run
- **Ban**: zero `loadEnvFile` in app runtime, zero ad-hoc dotenv parsing in app code

**Endpoints**:

- POST `/q`; auth against `SECRET_AUTH_TOKEN`
- GET `/sup`; auth against `SECRET_AUTH_TOKEN`

**Business Logic**:

- Status: `PENDING | PROCESSING | COMPLETED | FAILED | CANCELLED`
- Task ID: `base64("provider:originalTaskId")`
- Pick: `modal` (temporary)
