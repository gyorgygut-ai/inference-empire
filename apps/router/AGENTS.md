# apps/worker-router/AGENTS.md

## Rules for Agents

### Critical Specs

- Endpoints: `POST /infer`, `GET /inquire`
- Provider dispatch: read URLs from environment (`BEAM_URL`, `BEAM_TASK_API`, `FLASH_URL`, `FLASH_ENDPOINT`); contracts carry input/output schemas only
- Auth token: `AUTH_TOKEN` environment variable, generated once per deployment, never written to deploy output
- Task ID: `base64("provider:originalTaskId")` — beam: task UUID from `.put()`, flash: endpoint call ID
- Status enum: `PENDING | PROCESSING | COMPLETED | FAILED | CANCELLED`
- v1 picks beam, but selection function is separate for future expansion
- Code must be minimal, simple and stupid — no magic, no `any`, no ifs without `{}`, no semis

### Golden Rules

- Specs are authoritative — code must match them
- Exact touched files and lines to finish task; no less, no more
- Adherence to specs, key decisions and golden rules is non-negotiable

### Workflow

**Read before writing code**:

- `task-id.ts` — encode/decode with `btoa`/`atob`
- `pick-task-handler.ts` — v1 returns `'beam'`
- `router.ts` — itty-router endpoints