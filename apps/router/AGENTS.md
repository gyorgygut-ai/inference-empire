# Worker Router AGENTS.md

## Golden Rules

- Use conventional commits
- Specs are authoritative: code must match them
- Exact touched files and lines to finish task; no less, no more
- Adherence to specs, key decisions and golden rules is non-negotiable

## App Context

- Cloudflare Worker in TypeScript acting as stateless router
- Deploys once per worker contract (e.g., `router-flux2`, `router-krea2`)
- Accepts async inference requests via `POST /submit`
- Never retains task state — stateless by design
- Returns immediate confirmation `{task_id, provider}` to caller
- Caller manages task lifecycle via polling

## Architecture

Router Endpoints:
- `POST /submit` — Accept `{input: {...}}`, validate, submit to provider
- `GET /result/{task_id}` — Caller polls for completion (implement if needed later)

Provider Selection:
- **Default (v1):** Always picks Modal
- **Extensible:** Selection logic lives in `selection.ts` and can be extended to round-robin, priority-based, or reuse infra-router chain later
- **Per-contract deployment:** Each worker type deploys its own router instance

Contract Handling:
- Load contract JSONs from `packages/contracts/src/{worker}.json`
- Validate input against contract input schema at the boundary
- Source of truth: contract JSONs must match implementation

Provider Integration:
- **Modal adapter:** Uses `modal.Cls.from_name().method.spawn()` pattern matching existing workers
- **Beam adapter:** Uses `beam` SDK task queue pattern matching existing workers
- **Flash/RunPod adapter:** Uses `runpod_flash` SDK endpoint pattern matching existing workers
- Follows existing worker codesmith patterns (e.g., `worker_modal_cls_flux2_klein9b.py`)

## Worker → Chat Mapping
(Example with modal, refers to chat-ui/AGENTS.md)
- `flux2` `flux2_klein9b` — both: **(a) direct handler** (no LLM) context `flux2_klein9b` boxes + prompt → image `presigned_url` → Artifacts **(b) LLM tool-call** `flux2_klein9b` tool with same inputs → image `presigned_url` → Artifacts — per `flux2_klein9b.json:4-14`

## State
- No persistence after router restart (stateless)
- Caller manages task tracking via polling

## Coding Style & Standards
- No semicolons (`semi: ["error", "never"]`) to match face-value rules
- ESLint rules non-negotiable
- Existing linting config reused
- TypeScript strict mode enabled

## Test Strategy
- Unit tests for each provider adapter using mocked SDKs
- Input validation tests using real contract JSONs
- Provider selection tests for extensibility validation
- Test selection via filename: `-k "not e2e"` / `-k "e2e"` (per workers/AGENTS.md)