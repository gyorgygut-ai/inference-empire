# Router App

Stateless task queue api router, routing across urls from `WorkerServiceContract`.

---

## NX: `functions`

**Tasks**:

- `dev-flux2`:
  - continuous: true
  - dependsOn `predev` and `workers-flux2:deploy-beam`
  - command: [
      GENERATED_AUTH_TOKEN=$ROUTER_GENERATED_AUTH_TOKEN,
      npx tsx tools/serve-netlify-functions.ts --port 4000
    ]
  - inputs:
    - "{workspaceRoot}/packages/contracts/worker-service/flux2-deploy.contract.ts"
    - "{workspaceRoot}/packages/contracts/task-queue-service/flux2-dev.contract.ts"
  - "readyWhen": { "signal": true }
  - Netlify adapter emits its actual listening URL through public `emitReadySignal` after the server listens
- `dev-krea2`:
  - continuous: true
  - dependsOn `predev` and `workers-krea2:deploy-beam`
  - command: [
      GENERATED_AUTH_TOKEN=$ROUTER_GENERATED_AUTH_TOKEN,
      npx tsx tools/serve-netlify-functions.ts --port 4025
    ]
  - inputs:
    - "{workspaceRoot}/packages/contracts/worker-service/krea2-deploy.contract.ts"
    - "{workspaceRoot}/packages/contracts/task-queue-service/krea2-dev.contract.ts"
  - "readyWhen": { "signal": true }
  - Netlify adapter emits its actual listening URL through public `emitReadySignal` after the server listens
- `predev`
  - dependsOn `prebuild`
- `build`:
  - dependsOn `prebuild`
- `prebuild`:
  - dependsOn `["^prebuild", "generate-*"]`
- `deploy-flux2`:
  - dependsOn `prebuild` and `workers-flux2:deploy-beam`
  - command: [
      WORKER_URL_BEAM=$WORKER_RESOLVED_BEAM_URL,
      GENERATED_AUTH_TOKEN=$ROUTER_GENERATED_AUTH_TOKEN,
      netlify deploy --siteId={options.siteId}
    ]
  - inputs:
    - "{workspaceRoot}/packages/contracts/worker-service/flux2-deploy.contract.ts"
    - "{workspaceRoot}/packages/contracts/task-queue-service/flux2-deploy.contract.ts"
  - siteId: `cd41f060-bbdf-49fa-82a6-20d7ba136853`
- `deploy-krea2`:
  - dependsOn `prebuild` and `workers-krea2:deploy-beam`
  - command: [
      WORKER_URL_BEAM=$WORKER_RESOLVED_BEAM_URL,
      GENERATED_AUTH_TOKEN=$ROUTER_GENERATED_AUTH_TOKEN,
      netlify deploy --siteId={options.siteId}
    ]
  - inputs:
    - "{workspaceRoot}/packages/contracts/worker-service/krea2-deploy.contract.ts"
    - "{workspaceRoot}/packages/contracts/task-queue-service/krea2-deploy.contract.ts"
  - siteId: `cd41f060-bbdf-49fa-82a6-20d7ba136853`

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
