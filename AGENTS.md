# Inference Empire

**Value Proposition**: Monorepo for inference workers, tooling and whitelabel frontends.

---

## Architecture

**Workers**:

- `Role`: do inference tasks on multiple cloud GPU providers
- [Read Before Coding](./specs/WORKERS.md)

**Routers**:

- `Role`: mediate requests between UI and best provider for request
- [Read Before Coding](./specs/ROUTERS.md)

**Frontends**:

- `Role`: provide UIs for interacting with inference workers
- [Read Before Coding](./specs/FRONTENDS.md)

**Orchestration**:

- `Scalable`: workers implement one shared contract for multiple providers
- `Reusable`: whitelabel frontends and routers; one app can have multiple nx targets
- `Guarded`: all routers and workers are strictly protected `Authorization tokens`
- `Secure`: frontend targets consume token at build time to use it via `proxy` server
- `Critical`: these keywords are NOT marketing copy; but strict maintenance requirements

> Examples:
>
> - `Free AI Video Generator` <-> `Video-Gen Router` <-> `Some LTX-2 Worker`
> - `Phony Banana Web UI` <-> `Phony Banana Router` <-> `Some Phony Banana Worker`

---

## NX Workspace Management

**Activate Skill**:

- `.opencode/skills/nx-workspace`

**Critical Tools**: `nx graph`, `nx generators`, `nx executors` must be maintained and used
**verify command**: `audit` -> `lint` -> `build` -> `test`, each tier can fail verification
