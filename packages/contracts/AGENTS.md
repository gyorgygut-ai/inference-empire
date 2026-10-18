# Contracts

**Worker Service**:

- **Files**: `{workspaceRoot}/packages/contracts/worker-service/worker-service.{schema|contract}.ts`
- **Schema**: `WORKER_RESOLVED_{BEAM|MODAL|FLASH}_URL`; `envFilePath`
- **Contract.envFilePath.**: `{workspaceRoot}/dist/{taskName}/`

**Task Queue Service**:

- **Files**: `{workspaceRoot}/packages/contracts/task-queue-service/task-queue-service.{schema|contract}.ts`
- **Schema**: `ROUTER_RESOLVED_URL`; `ROUTER_GENERATED_AUTH_TOKEN`; `envFilePath`
