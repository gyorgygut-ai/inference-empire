# Worker Router

**Critical Specs**:

- Stateless Cloudflare Worker
- Routes requests to providers implementing the contract
- Uses Typescript, no "as any" escape hatches, strict DI patterns
- Implements its own shared contracts of endpoints

 **Each deployment depends on**:

- deployed worker contract outputs: `dist/apps/gpu-workers-flux2/contract.json`, `dist/apps/gpu-workers-tiny-sd/contract.json`
- generated provider manifest: `src/lib/providers.generated.json` (from `build-manifest` target reading dist/ contracts)
- consumer receives auth token from `dist/apps/worker-router/contract.json` at build time

**Each deployment is depended on**:

- any consumer app depending on that configuration

 **Authentication**:

- Bearer auth header guarding all endpoints
- Auth token generated at build-manifest time, written to `dist/apps/worker-router/contract.json`
- Token is pushed to Cloudflare via `wrangler secret put` during `worker-router:deploy`
- Consumer apps read token from `dist/apps/worker-router/contract.json` at their build time (e.g. `chat-ui/src/lib/router-config.ts`)

**Endpoints**:

- POST: queue (200, 400)
  - takes { input: **contract** }
  - picks which of the provider deployments to forward to
  - first version always picks Modal for quick testing
  - trategy pattern for provider requests implemented regardless
  - responds { task_id: "<encoded from provider name + received task id>" }

- GET: task (200, 404)
  - takes { task_id }
  - decodes task id to get original task id + provider target
  - polls that providers task via its API by original task id
  - responds
    {
    output?: full output contract type, e.g. "flux2:
    status: "BUSY" | "REJECTED" | "DONE" - provider statuses mapped to these values
    }

 **Example Use Case**

- `nx run worker-router:deploy` triggers the full Nx chain:
  1. `gpu-workers-flux2:deploy-*` writes `dist/apps/gpu-workers-flux2/contract.json`
  2. `gpu-workers-tiny-sd:deploy-*` writes `dist/apps/gpu-workers-tiny-sd/contract.json`
  3. `worker-router:build-manifest` reads dist/ contracts → writes `dist/apps/worker-router/contract.json` (token + endpoints)
  4. `worker-router:deploy` pushes token to Cloudflare secrets, deploys both `--env flux2` and `--env tinysd`
  5. Consumer `build` reads `dist/apps/worker-router/contract.json` for token + router URLs
- Runtime:
  - Consumer can send tasks to router, sending token and input
  - Router receives request at /queue, pick provider, sends task to provider queue
  - Upon success, responds with task id using the unified contract
  - Client can poll router /task to get status and any output (non-null output means done)
