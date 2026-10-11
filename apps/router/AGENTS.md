# Router App

Stateless router routing across worker implementations of a contract.

**NX Project**:

- **Targets**: `router-{worker}`
- **Depends on**: `{worker}:dev`, `{worker}:deploy`
- **Contract**: `@packages/contracts/{worker}/inference.json`

**target:generate-api**:

- **input**: the worker contract schema
- **output**: api + worker contract, `dist/{worker}_api.json`

**target:generate-ts**:

- **input**: `dist/{worker}_api.json`
- **output**: generated TS, `generated/{worker}_api.ts`

**Environment**:

- `APP_URL` resolved on `dev` + `deploy`
- `SECRET_AUTH_TOKEN`: generates brand new token each run

**Endpoints**:

- POST `/q`; auth against `SECRET_AUTH_TOKEN`
- GET `/sup`; auth against `SECRET_AUTH_TOKEN`

**Business Logic**:

- Status: `PENDING | PROCESSING | COMPLETED | FAILED | CANCELLED`
- Task ID: `base64("provider:originalTaskId")`; beam: task UUID`, flash: call ID
- Pick hardcoded to `modal`; this is temporary; but other provider code paths maintained
