# Router App

Stateless task queue api router, routing across urls from `WorkerServiceContract`.

---

## NX: `router:dev-flux2`

**Cmd**: `netlify dev`
**Before `dev-flux2`**:

  - **Needs** `flux2` `WorkerServiceContract`
  - **Fulfills** `WorkerServiceContract.ROUTER_RESOLVED_URL`
  - **Fulfills** `WorkerServiceContract.ROUTER_GENERATED_AUTH_TOKEN`
  - **Generates** flux2 api types to `{projectRoot}/dist/`

## NX: `router:deploy-flux2`

**Command**: `netlify deploy`

**MUST DO before `deploy-flux2`**:

  - **Needs** `flux2` `WorkerServiceContract`
  - **Fulfills** `WorkerServiceContract.ROUTER_RESOLVED_URL`
  - **Fulfills** `WorkerServiceContract.ROUTER_GENERATED_AUTH_TOKEN`
  - **Generates** flux2 api types to `{projectRoot}/dist/`

---

## Structure: `./src/`

**Netlify Function**

- `router_flux2.ts`:
  - serves: `/flux2/*`
  - loads: `flux2` api schema
  - hands request to `_shared/router.ts`
- `router_krea2.ts`:
  - serves: `/krea2/*`
  - loads: `krea2` api schema
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

- POST `/q`: queue task; Auth against `WorkerServiceContract.ROUTER_GENERATED_AUTH_TOKEN`
- GET `/sup`: fetch task; Auth against `WorkerServiceContract.ROUTER_GENERATED_AUTH_TOKEN`

**Business Logic**:

- Status: `PENDING | PROCESSING | COMPLETED | FAILED | CANCELLED`
- Task ID: `base64("provider:originalTaskId")`
- Pick: `modal` (hardcoded, temporary)
