# packages/task-queue-client/AGENTS.md

## Rules for Agents

### Critical Specs

- Client for task-queue API: `POST /q`, `GET /sup`
- One call in, result out — submit and poll encapsulated
- Config is the value bag only: base URL, token, poll interval, timeout
- Dependencies are separate arguments: `fetchImpl`, which defaults to global `fetch`, and optional `AbortSignal`
- Polls until terminal or timeout — terminal wire values are `COMPLETED | FAILED | CANCELLED`
- Task IDs are opaque — pass them back, never decode
- No env reads, no module state, no singleton, no global `fetch` read behind the caller's back
- Code must be minimal, simple and stupid — no magic, no `any`, no ifs without `{}`, no semis

### Golden Rules

- Specs are authoritative — code must match them
- Exact touched files and lines to finish task; no less, no more
- Adherence to specs, key decisions and golden rules is non-negotiable
