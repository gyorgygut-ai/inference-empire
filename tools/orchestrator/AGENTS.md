# Orchestrator

## Executors

**orchestrator:run-command**:

- **Problem**: A task needs to declare it depends a contract or fulfills it
- **Approach**: `options.needs`, `options.fulfills` 
- **Outcome**: 
- **Acceptance**:
  - `execute`: composes unaltered `nx:run-command`
  - `needs`: looks up `contract.env` using `envFilePath`
  -> `envFile`: injects `envFilePath || options.envFile` as `envFile`
  - `output`: captures any output via `terminalOutput`
  -> `fulfills`: upserts `output value` into `envFile`

---

## Examples

**Contracts**: [packages/contracts](packages/contracts/AGENTS.md)

**1. Contract**:

- **File**: `packages/contracts/some-service.contract.ts`
- `envFilePath`: `{workspaceRoot}/dist/{taskName}/contract.env`

**2. Producer**:
`"producer-app:deploy": {
  "command": "tools/deploy-some-service.ts",
  "options": {
    fulfills: { "contract": "some-service", "key": "SOME_SERVICE_RESOLVED_URL" }
  } 
}`
- **Flow**: `deploy-some-service.ts` -> `SOME_SERVICE_RESOLVED_URL` -> `{workspaceRoot}/dist/{taskName}/contract.env`

**3. Consumer**:

- **Task**: `"consumer-app:deploy": {
"command": "npm run my-dev-server",
"options": {
    needs: { "contract": "some-service" }
  } 
}`
- **Flow**: `nx:run-commands` -> `envFile: {workspaceRoot}/dist/{taskName}/contract.env` -> `my-dev-server`
