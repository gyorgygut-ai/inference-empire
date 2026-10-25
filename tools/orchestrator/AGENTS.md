# Orchestrator

## URL Resolvers

**Problem**: A deployed URL must be resolvable anytime, without re-deploying, dashboard, or SDK scripts
**Approach**: `src/get-{provider}-url.ts` — one executable per provider; prints the deployed URL as the last line of stdout; diagnostics on stderr; non-zero exit on failure
**Outcome**: project.json targets only invoke the tool and echo its output into an env var

- **get-beam-url <app-name>**: ``
- **get-modal-url <app-name> <function-name>**: ``
- **get-flash-url <endpoint-name>**: ``
- **get-netlify-url <site-id>**: ``
- **get-vercel-url <project-id>**: ``

---

## Executors

**orchestrator:run-command**:

- **Problem**: A task needs to declare it depends a contract or fulfills it
- **Approach**: `options.needs[]`, `options.fulfills[]`
- **Outcome**: 
- **Acceptance**:
  - **Safety**: Nx 23 has no `--dry-run` for `run`/`run-many`/`affected`; the flag is forwarded as an unknown option and every task, dependencies included, executes
  - `execute`: composes unaltered `nx:run-command`
  - `needs[]`: resolves each contract `envFilePath` against `context.root`, merges into the command env; `contractKey` is the key that must be present
  -> `envFile`: read and injected, not forwarded
  - `output`: captures any output via `terminalOutput`
  -> `fulfills[]`: upserts `output value` into `envFilePath` under `contractKey`; a key the contract does not own is rejected

---

## Examples

**Contracts**: [packages/contracts](packages/contracts/AGENTS.md)

**1. Contract**:

- **File**: `packages/contracts/worker-service/flux2-dev.contract.ts`
- `envFilePath`: `dist/flux2/dev.env`

**2. Producer**:
`"producer-app:deploy": {
  "command": "tools/deploy-some-service.ts",
  "options": {
    fulfills: [{ "contract": "WorkerServiceContractFlux2Deploy", "contractKey": "WORKER_RESOLVED_BEAM_URL" }]
  } 
}`
- **Flow**: `deploy-some-service.ts` -> `WORKER_RESOLVED_BEAM_URL` -> the contract's `envFilePath`

**3. Consumer**:

- **Task**: `"consumer-app:deploy": {
"command": "npm run my-dev-server",
"options": {
    needs: [{ "contract": "WorkerServiceContractFlux2Dev" }, { "contract": "TaskQueueServiceContractFlux2Dev" }]
  } 
}`
- **Flow**: `run-command` -> `needs[]` -> `my-dev-server`
