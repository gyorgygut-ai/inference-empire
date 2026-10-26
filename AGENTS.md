# Inference Empire

**Value Proposition**: Monorepo for inference workers + frontends + tooling.

---

## Key Projects

- [Router](./apps/functions/AGENTS.md)
- [Workers](./apps/workers/AGENTS.md)
- [Face Value](./apps/face-value/AGENTS.md)

---

## Non-negotiables

**Correct**:

- **Goal**: Spec adherence across the codebase without gaps
- **Approach**: Code matched to authoritive specs; NOT specs to code
- **Outcome**: Code fulfilling acceptance criteria as specs dictate

**No guesses**:

- **Goal**: Idiomatic, documented patterns instead of hand-rolling and guesses
- **Approach**: Use the `nx-*`, `python-uv` skills and the `nx mcp` to verify
- **Outcome**: Trial-and-error loops eliminated; simple, reliable codebase

---

## Orchestration

**Dev URL Discovery**:

- **Problem**: `consumer:dev` needs `continuous` `producer:dev`'s server url
- **Consumer**: `consumer` has `dependsOn: "producer:dev", waitFor: "ready"`
- **Producer**: `producer` has `"readyWhen": { "signal": true }` and emits its actual listening URL through public `emitReadySignal` after the server listens
- **Outcome**: nx hands `process.env.NX_READY_URL` to `consumer` after `ready signal`
- **Acceptance**:
  - Vendor local dev servers wrapped in `serve-*` scripts
  - serve script starts vendor on `args.port`
  - serve script emits ready signal when server is up
  - serve script does not do anything else; no env juggling

**Deploy URL Discovery**:

- **Problem**: `app-x:deploy` needs `app2:deploy`'s deployed url
- **Approach**: `app-x` dependsOn `app2:deploy` + requests it's url
- **Tool**: [Orchestrator executes](tools/orchestrator/AGENTS.md)
- **Outcome**: `app-x:deploy` + `inputs` gets `process.env.APP_X_DEPLOYED_URL`
 - **Acceptance**:
  - No custom  `deploy-*` scripts; use vendor cli directly
  - `app-x:deploy` must declare contract as task `input`
  - `contract` defines how to `resolve` values from it's `schema`
  - `executor` detects input and hands off contract values
  - `app2` receives values in `env`; NO manual env juggling

**Deploy URL & Contracts**:

- **Problem**: `app-y:task` depends on a runtime data contract
- **Approach**: [Orchestrator injects](tools/orchestrator/AGENTS.md)
- **Outcome**: Contract extended into `input`; `:task` data in `process.env`

---

## Key Targets

**Acceptance**: `face-value:dev`

- `WorkerServiceFlux2DeployContract` resolves required values
- `TaskQueueServiceFlux2DevContract` resolves required values
- `flux2 worker`: ping `WORKER_RESOLVED_BEAM_URL` suceeds
- `flux2 router`: ping `http://127.0.0.1:4000` suceeds
- `face-value`: ping `http://127.0.0.1:3000` suceeds

**Acceptance**: `functions:dev-krea2`

- `WorkerServiceKrea2DeployContract` resolves required values
- `TaskQueueServiceKrea2DevContract` resolves required values
- `krea2 worker`: ping `WORKER_RESOLVED_BEAM_URL` suceeds
- `krea2 router`: ping `http://127.0.0.1:4025` suceeds

**Acceptance**: `face-value:deploy`

- `WorkerServiceFlux2DeployContract` resolves required values
- `TaskQueueServiceFlux2DeployContract` resolves required values
- `flux2 worker`: ping `WORKER_RESOLVED_BEAM_URL` suceeds
- `flux2 router`: ping `ROUTER_RESOLVED_URL` suceeds
- `face-value`: deploy suceeds

---

## Verification

**Non-negotiable**:

- **Proof**: the verification chain must prove all changes
- **Progress**: tier-by-tier; until all passed or failure
- **Failures**: run `lint-fix`; report; investigate; fix; restart verification
- **Defaults**: `verify*` tasks must be in `nx.json`
- **Readiness**: assert after `finite` deps finish or `continuous` signal ready
- **Tidiness**: 6 lines per test criteria, at the most: `setup` \n `act` \n `assert`

**💪🏾 Full Chain**: `verify`

-> `npx nx run-many -t verify --nxBail`
-> runs `verify-tier-1` gates `verify-tier-2` gates `verify-tier-3`

**🧐 Tier 1: audit**: `verify-tier-1-audit` 

-> **dependsOn**: `["lint", "build", "test-unit"]`

**🏡 Tier 2: dev**: `verify-tier-2-dev`

-> **dependsOn**: `["verify-tier-1*", "acceptance:dev*", "e2e:dev*"]`
-> **test:acceptance:dev**: `./tools/test/acceptance.dev.test.ts`
-> **test:acceptance:dev-krea2**: `./tools/test/acceptance.dev-krea2.test.ts`
-> **test:e2e:dev**: `nx:no-op`

**🏰 Tier 3: deploy**: `verify-tier-3-deploy`

-> **dependsOn**: `["verify-tier-2*", "acceptance:deploy*", "e2e:deploy*"]`
-> **test:acceptance:deploy**: `./tools/test/acceptance.deploy.test.ts`
-> **test:e2e:deploy**: `nx:no-op`
