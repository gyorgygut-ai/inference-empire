# Inference Empire

**Value Proposition**: Monorepo for inference workers + frontends + tooling.

---

## Key Projects

- [Router](./apps/router/AGENTS.md)
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

**Dependencies**:

- **Tool**: `dependsOn`, `targetDefaults`, `(implicit)Dependencies` 
- **Problem**: Apps need to run / deploy in a clearly defined order 
- **Approach**: `build`;`dev`;`deploy` defined per project; otherwise not needed
- **Outcome**: Chained tasks triggering their dependencies; NO repetitive boilerplate
- **`dependsOn` patterns**: 
  - `dev`: 
  - `build`: 
  - `deploy`: 

**Service Contract**:

- **Package**: [packages/contracts](packages/contracts/AGENTS.md)
- **Problem**: Apps need to locate each other and talk
- **Approach**: `contract.ts` materializes `zod` `schema.ts`
- **Outcome**: One app declares need; another fulfills it

**Contract Delegation**:

- **Package**: [orchestrator/run-command](tools/orchestrator/AGENTS.md)
- **Problem**: Contract needs and fulfillments need declared
- **Approach**: Executor delegates artifacts, non-cacheable 
- **Outcome**: Pain-free, type-safe contracts across apps

**Data Schemas**:

- **Package**: [packages/schemas](packages/schemas/AGENTS.md)
- **Problem**: Apps need to know how to communicate
- **Approach**: JSON schemas -> zod / TS generated on-demand
- **Outcome**: Schema changes propagate; end-to-end type safety

---

## Key Targets

**Acceptance**: `npx nx run router:dev-flux2`

- `flux2` `WorkerServiceContract` fulfilled
  -> ping `WORKER_RESOLVED_BEAM_URL` suceeds
  -> `flux2` `TaskQueueServiceContract` fulfilled
    -> `ROUTER_RESOLVED_URL` eq `http://127.0.0.1:5050`
    -> ping `ROUTER_RESOLVED_URL` suceeds
      -> ping `face-value` `http://127.0.0.1:3000` succeeds

**Acceptance**: `npx nx run router:deploy-flux2`

  - `flux2` `WorkerServiceContract` fulfilled
    -> ping `WORKER_RESOLVED_BEAM_URL` suceeds
    -> `flux2` `TaskQueueServiceContract` fulfilled
      -> ping `ROUTER_RESOLVED_URL` suceeds
        -> ping `face-value` succeeds

**VERIFICATION**:

- **Tool**: `tools/acceptance.{dev|deploy}.test.ts`
- **Approach**:
  - CLEAN `dist` folders before all
  - NO test runs before NX chain finishes
  - NO hand-rolled polling for waiting; relying on NX
  - MAX. 6 lines per test case: setup \n act \n assert
- **Outcome**: Deterministic change verification
