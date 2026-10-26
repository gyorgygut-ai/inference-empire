# Router App

Stateless task queue api router, routing across urls from `WorkerServiceContract`.

---

## NX: `functions`

**Tasks**:

- `dev`:
  - continuous: true
  - defaultConfiguration: "flux2"
  - dependsOn `predev` and the selected family's `workers-{family}:deploy-beam`
  - command: [
      GENERATED_AUTH_TOKEN=$ROUTER_GENERATED_AUTH_TOKEN,
      netlify dev --port {options.port}
    ]
  - inputs for the selected family:
    - "{workspaceRoot}/packages/contracts/worker-service/{family}-deploy.contract.ts"
    - "{workspaceRoot}/packages/contracts/task-queue-service/{family}-dev.contract.ts"
  - "readyWhen": { "signal": true }
  - Netlify adapter emits its actual listening URL through public `emitReadySignal` after the server listens
  - configurations: {
      "flux2": { port: 4000 },
      "krea2": { port: 4025 }
    }
  - family mapping:
    - `flux2`: `workers-flux2:deploy-beam`, `worker-service/flux2-deploy.contract.ts`, `task-queue-service/flux2-dev.contract.ts`
    - `krea2`: `workers-krea2:deploy-beam`, `worker-service/krea2-deploy.contract.ts`, `task-queue-service/krea2-dev.contract.ts`
- `predev`
  - dependsOn `prebuild`
- `build`:
  - dependsOn `prebuild`
- `prebuild`:
  - dependsOn `["^prebuild", "generate-*"]`
- `deploy`:
  - dependsOn `prebuild` and the selected family's `workers-{family}:deploy-beam`
  - command: [
      WORKER_URL_BEAM=$WORKER_RESOLVED_BEAM_URL,
      GENERATED_AUTH_TOKEN=$ROUTER_GENERATED_AUTH_TOKEN,
      netlify deploy --siteId={options.siteId}
    ]
  - inputs for the selected family:
    - "{workspaceRoot}/packages/contracts/worker-service/{family}-deploy.contract.ts"
    - "{workspaceRoot}/packages/contracts/task-queue-service/{family}-deploy.contract.ts"
  - configurations: {
      "flux2": { siteId },
      "krea2": { siteId }
    }
  - family mapping:
    - `flux2`: `workers-flux2:deploy-beam`, `worker-service/flux2-deploy.contract.ts`, `task-queue-service/flux2-deploy.contract.ts`
    - `krea2`: `workers-krea2:deploy-beam`, `worker-service/krea2-deploy.contract.ts`, `task-queue-service/krea2-deploy.contract.ts`

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
