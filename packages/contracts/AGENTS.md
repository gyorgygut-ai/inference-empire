# Contracts

**One contract per `{family}-{env}` scope**:

- **Files**: `{workspaceRoot}/packages/contracts/{service}/{family}-{env}.contract.ts`
- **Shape**: `{ keys: readonly string[]; envFilePath: string }`
- **envFilePath**: constant, relative to the workspace root; the executor resolves it against `context.root` and is its only reader/writer

**Worker Service**:

- **Keys**: `WORKER_RESOLVED_{BEAM|MODAL|FLASH}_URL`; the family's platform surface. A key may be unfulfilled until a target fulfills it; `needs[].contractKey` is what requires one
- **envFilePath**: `dist/{family}/{dev|deploy}.env`

**Task Queue Service**:

- **Keys**: `ROUTER_RESOLVED_URL`; `ROUTER_GENERATED_AUTH_TOKEN`; both fulfilled by the router chain
- **envFilePath**: `dist/{family}/{dev|deploy}.env`
