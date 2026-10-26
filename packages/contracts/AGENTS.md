# Contracts

**Critical**:

- Each contract is created manually, as needed
- There is NO one contract per model family requirement

**Structure**:

- **One file**  with `schema` + `contract` + `resolvers`
- **Schema**: `zod` schema describing typed fields
- **Command**: `path` to value resolve command

**Example**:

```
export const taskQueueServiceFlux2DeploySchema...
export const TaskQueueServiceFlux2DeployContract...

export const TaskQueueServiceFlux2DeployResolvers = {
  ROUTER_RESOLVED_URL: 'tools/orchestrator/src/get-netlify-url.ts --siteId="{options.siteId}"',
  ROUTER_GENERATED_AUTH_TOKEN: 'tools/generate-auth-token.ts',
}
```
