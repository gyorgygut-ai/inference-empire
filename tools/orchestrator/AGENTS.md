# Orchestrator

## Executors

**orchestrator:run-command**:

- **Problem**: A task needs to declare it depends a contract or fulfills it
- **Approach**: `options.needs[]`, `options.fulfills[]`
- **Outcome**: 
- **Acceptance**:
  - `execute`: composes unaltered `nx:run-command`
  - `needs[]`: resolves each contract `envFilePath` against `context.root`, merges into the command env
  -> `envFile`: read and injected, not forwarded
  - `output`: captures any output via `terminalOutput`
  -> `fulfills[]`: upserts `output value` into `envFilePath` under `contractKey`

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
