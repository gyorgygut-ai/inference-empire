# Router App

Stateless router routing across worker implementations of a contract.

- **Targets**: multiple, matching naming pattern `router-{worker}`
- **Depends on**: `{worker}:dev` + `{worker}:deploy`
- **Generated TS**: types from `inference` plus `api-task-queue` schemas; `generated/router-{worker}_contract.ts`

**Environment**:

- `APP_URL` resolved on `dev` + `deploy`
- `SECRET_AUTH_TOKEN`: generates new token on `build`

**Endpoints**:

- POST `/q`; auth against `SECRET_AUTH_TOKEN`
- GET `/sup`; auth against `SECRET_AUTH_TOKEN`

**Business Logic**:

- Status: `PENDING | PROCESSING | COMPLETED | FAILED | CANCELLED`
- Task ID: `base64("provider:originalTaskId")`; beam: task UUID`, flash: call ID
- Pick hardcoded to `modal`; this is temporary; but other provider code paths maintained
