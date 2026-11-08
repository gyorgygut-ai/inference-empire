# Router App

Stateless task queue api router, routing across worker urls.

---

## dev-flux2 ENV

**env**:
  - `PORT`: `${DEV_ROUTER_FLUX2_PORT}`
  - `AUTH_TOKEN`: `${SECRET_ROUTER_FLUX2_AUTH_TOKEN}`

**NX**:
  - **Cmd**: `wrangler dev` directly
  - **Readiness**: `{ continuous, readyWhen": { "url": "http://localhost:{env.DEV_ROUTER_FLUX2_PORT}" }}`
  - **Depends**: `predev`, `worker-flux2/deploy-beam`
  - **Types**: `predev` -> `prebuild` -> `^prebuild`
  - **WORKER_BEAM_URL**: get directly `{get-beam-url.ts(worker-flux2)}`

## deploy-flux2 ENV

**dotenv**:
  - `AUTH_TOKEN`: `${SECRET_ROUTER_FLUX2_AUTH_TOKEN}`

**NX**:
  - **Cmd**: `wrangler deploy`
  - **Depends**: `worker-flux2/deploy-beam`
  - **Types**: `build` -> `prebuild` -> `^prebuild`
  - **WORKER_BEAM_URL**: get directly `{get-beam-url.ts(worker-flux2)}`

# Other tasks

- **dev-tinysd**: Same as `dev-flux2`, but with `tinysd`
- **deploy-tinysd**: Same as `deploy-flux2`, but with `tinysd`
- **dev**: dependsOn `["dev-flux2", "dev-tinysd"]`
- **deploy**: dependsOn `["deploy-flux2", "deploy-krea"]`

---

## Structure: `./src/`

**Cloudflare Worker**

- `router_flux2.ts`:
  - loads: `flux2` api schema
  - hands request to `_shared/router.ts`
- `router_tinysd.ts`:
  - loads: `tinysd` api schema
  - hands request to `_shared/router.ts`

**_shared**:

- `router.ts`:
  - router entry
  - uses `itty-router`
  - endpoints: `/q` and `/sup`
  - delegates requests to `strategies`
- `strategies/strategy-beam.ts`:
- `strategies/strategy-modal.ts`:
- `strategies/strategy-flash.ts`:
- `services/pick-strategy.ts`: picks best strategy for task (hardcoded to return "beam")
- `services/create-strategy.ts`: creates strategy based on received `beam|modal|flash`

---

**Endpoints**:

- POST `/q`: queue task; Auth against `AUTH_TOKEN`
- GET `/sup`: fetch task; Auth against `AUTH_TOKEN`

**Business Logic**:

- Status: `PENDING | PROCESSING | COMPLETED | FAILED | CANCELLED`
- Task ID: `base64("provider:originalTaskId")`
