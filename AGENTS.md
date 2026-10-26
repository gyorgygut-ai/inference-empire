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
- **Producer**: `producer` has `readyWhen": { "signal": true }`
- **Outcome**: nx hands `process.env.NX_READY_URL` to `consumer` after `ready signal`

**Deploy URL Discovery**:

- **Problem**: `app-x:deploy` needs `app2:deploy`'s deployed url
- **Approach**: [Orchestrator executes](tools/orchestrator/AGENTS.md)
- **Outcome**: `app-x:deploy` + `inputs` gets `process.env.APP_X_DEPLOYED_URL`

**Deploy URL & Contracts**:

- **Problem**: `app-y:task` depends on a runtime data contract
- **Approach**: [Orchestrator injects](tools/orchestrator/AGENTS.md)
- **Outcome**: Contract extended into `input`; `:task` data in `process.env`

---

## Key Targets

TODO: ignore these rules for now; they are outdated

**Acceptance**: `npx nx run face-value:dev`

- `WorkerServiceFlux2DeployContract` resolves required values
- `TaskQueueServiceFlux2DevContract` resolves required values
- `flux2 worker`: ping `WORKER_RESOLVED_BEAM_URL` suceeds
- `flux2 router`: ping `http://127.0.0.1:4000` suceeds
- `face-value`: ping `http://127.0.0.1:3000` suceeds

**Acceptance**: `npx nx run functions:dev:krea2`

- `WorkerServiceKrea2DeployContract` resolves required values
- `TaskQueueServiceKrea2DevContract` resolves required values
- `krea2 worker`: ping `WORKER_RESOLVED_BEAM_URL` suceeds
- `krea2 router`: ping `http://127.0.0.1:4025` suceeds

**Acceptance**: `npx nx run face-value:deploy`

- `WorkerServiceFlux2DeployContract` resolves required values
- `TaskQueueServiceFlux2DeployContract` resolves required values
- `flux2 worker`: ping `WORKER_RESOLVED_BEAM_URL` suceeds
- `flux2 router`: ping `ROUTER_RESOLVED_URL` suceeds
- `face-value`: deploy suceeds

**Verifcation: Acceptance Tests**:

- **tools/acceptance.dev**: `npx nx run face-value:dev`
- **tools/acceptance.dev.krea2**: `npx nx run functions:dev:krea2`
- **tools/acceptance.deploy**: `npx nx run face-value:deploy`

**Verification: E2E Tests**:

- **tools/e2e.dev**: __ignore for now. postponed__
- **tools/e2e.deploy**: __ignore for now. postponed__

**Verification Rules**:

- Tests **MUST BE** proof of task chain verification
- **Idempotent**: CLEAN `dist` folders before all
- NO test runs before NX chain finishes
- NO hand-rolled polling for waiting; relying on NX
- MAX. 6 lines per test case: setup \n act \n assert
