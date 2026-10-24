# Router App

Stateless task queue api router, routing across urls from `WorkerServiceContract`.

---

## NX: `functions`

**Tasks**:

- `dev-flux2`:
  - dependsOn `predev`
  - cmd: `tools/serve-netlify-functions.ts`
  - waits: `router:dev-flux2` must listen + READY
  - needs[]: `WorkerServiceContractFlux2Dev`
  - needs[]: `TaskQueueServiceContractFlux2Dev`
  - fulfills.contract: `TaskQueueServiceContractFlux2Dev`
  - fulfills.contractKey: `ROUTER_RESOLVED_URL`
- `predev`
  - dependsOn `prebuild`
- `build`:
  - dependsOn `prebuild`
- `generate-auth-token`
  - cmd: `tools/geneate-auth-token.ts`
  - fulfills.contract: `TaskQueueServiceContract{Family}{Dev|Deploy}`
  - fulfills.contractKey: `ROUTER_GENERATED_AUTH_TOKEN`
- `prebuild`:
  - dependsOn `["^prebuild", "generate-*"]`
- `deploy-flux2`:
  - dependsOn `build`
  - cmd: `netlify deploy`
  - needs[]: `WorkerServiceContractFlux2Deploy`
  - needs[]: `TaskQueueServiceContractFlux2Deploy`
  - fulfills.contract: `TaskQueueServiceContractFlux2Deploy`
  - fulfills.contractKey: `ROUTER_RESOLVED_URL`

- `dev-krea2`: same as `dev-flux2`; but with `krea2`
- `deploy-krea2`: same as `deploy-flux2`; but with `krea2`

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

- POST `/q`: queue task; Auth against `TaskQueueServiceContract.ROUTER_GENERATED_AUTH_TOKEN`
- GET `/sup`: fetch task; Auth against `TaskQueueServiceContract.ROUTER_GENERATED_AUTH_TOKEN`

**Business Logic**:

- Status: `PENDING | PROCESSING | COMPLETED | FAILED | CANCELLED`
- Task ID: `base64("provider:originalTaskId")`
- Pick: `modal` (hardcoded, temporary)
