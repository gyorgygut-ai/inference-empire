# Worker Router

Cloudflare Worker in TypeScript that routes worker input contracts to GPU providers.

## Golden Rules

- Use conventional commits
- Specs are authoritative: code must match them
- Exact touched files and lines to finish task; no less, no more
- Adherence to specs, key decisions and golden rules is non-negotiable

## App Context

- Cloudflare Worker written in TypeScript
- One deployment per worker contract (`worker-router-flux2`, `worker-router-krea2`, etc.)
- Accepts async inference requests via `POST /submit`
- Stateless by design — no task storage, no persistence
- Returns immediate confirmation `{task_id, provider}` to caller
- Caller manages task lifecycle via polling

## Architecture

Router Endpoints:
- `POST /submit` — Accept `{input: {...}}`, validate, submit to provider
- `GET /result/{task_id}` — Caller polls for completion (implement if needed later)

## Contract Handling

- Contracts live in `packages/contracts/src/{name}.json` — source of truth
- Deploy command passes contract path: `--contract=packages/contracts/src/flux2_klein9b.json`
- Worker reads contract at build time and generates TypeScript types from the JSON
- Runtime validates requests against pre-generated types (no on-the-fly type generation)
- Contract JSONs must match implementation exactly
- Never hand-write contract JSONs; update JSON first, then code

## Provider Selection (Strategy Pattern)

- Provider selection logic lives in `src/selection.ts`
- **Default (v1):** Always picks Modal
- **Extensible:** Strategy pattern — add Beam and Flash strategies later without changing router core
- Each strategy implements a common interface for submit and status
- No `any`, no `as` escape hatches — all code must be type-safe and test-first designed for DI

## Provider Integration

- **Modal adapter:** Uses `modal.Cls.from_name().method.spawn()` pattern matching existing workers
- **Beam adapter:** Uses `beam` SDK task queue pattern matching existing workers
- **Flash/RunPod adapter:** Uses `runpod_flash` SDK endpoint pattern matching existing workers
- Follows existing worker codesmith patterns (e.g., `worker_modal_cls_flux2_klein9b.py`)

## Coding Style & Standards

- No semicolons (`semi: ["error", "never"]`) to match face-value rules
- ESLint rules non-negotiable
- Existing linting config reused
- TypeScript strict mode enabled
- No `any`, no `as` escape hatches
- All code must be test-first designed for Dependency Injection

## Test Strategy

- Unit tests for each provider adapter using mocked SDKs
- Input validation tests using real contract JSONs
- Provider selection tests for extensibility validation
- Test selection via filename: `-k "not e2e"` / `-k "e2e"` (per workers/AGENTS.md)

## Deployment

- Nx project: `worker-router`
- One deploy target per worker contract, each passing `--contract=<path>` to wrangler
- Example: `nx run worker-router:deploy:flux2`
- Each deployment creates a separate Cloudflare Worker with its own contract types