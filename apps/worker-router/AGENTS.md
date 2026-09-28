# apps/worker-router/AGENTS.md

## Rules for Agents

### Critical Specs

- Endpoints: `POST /infer`, `GET /inquire`
- Provider dispatch: read URLs from `contract.json` `providers` section
- Auth token: static string from `contract.json` `authToken`
- Task ID: `base64("provider:originalTaskId")` — modal: `call.object_id`, beam: task UUID from `.put()`
- Status enum: `PENDING | PROCESSING | COMPLETED | FAILED | CANCELLED`
- v1 always picks modal, but selection function is separate for future expansion
- Code must be minimal, simple and stupid — no magic, no `any`, no ifs without `{}`, no semis

### Golden Rules

- Specs are authoritative — code must match them
- Exact touched files and lines to finish task; no less, no more
- Adherence to specs, key decisions and golden rules is non-negotiable

### Workflow

**Read before writing code**:

- `task-id.ts` — encode/decode with `btoa`/`atob`
- `pick-task-handler.ts` — v1 always returns `'modal'`
- `router.ts` — itty-router endpoints