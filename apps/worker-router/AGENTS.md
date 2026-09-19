# Worker Router

**Critical Specs**:

- Stateless Cloudflare Worker
- Routes requests to providers implementing the contract
- Uses Typescript, no "as any" escape hatches, strict DI patterns
- Implements its own shared contracts of endpoints

**Each deployment depends on**:

- an input/output contract e.g. "flux2" - generates TS on deploy
- the deployed worker implementations of that contract (for usls)
- reusable, one deployment of router per contract type, configured

**Each deployment is depended on**:

- any consumer app depending on that configuration

**Authentication**:

- Bearear auth header guarding all endpoints
- Auth token generated at deploy (build) time
- Consumer apps receive auth token at build time to use at runtime

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

- Router deployed with build time deps:
  - Using packages/contracts/src/small_vision.json
  - Deployed provider worker urls
- Any consumers depending on that router configuration
  - Redeployed, receiving contracts and generated token at build time
- Runtime:
  - Consumer can send tasks to router, sending token and input
  - Router receives request at /queue, pick provider, sends task to provider queue
  - Upon success, responds with task id using the unified contract
  - Client can poll router /task to get status and any output (non-null output means done)
