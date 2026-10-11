# Inference Empire

**Value Proposition**: Monorepo for inference workers + frontends + tooling.

- **ACTIVATE**: `./opencode/skills/nx-workspace`
- **Paths**: assume `{projectRoot}` in relative paths
- **Specs**: specs are always authoritive. Code must match specs
- **NON-gaps**: good code without specs, example names not coded

---

## Monorepo Orchestration

> DO NOT stuff everything into workspace-plugin.
> One generic job per tool tells the story clean.

**Generated Types**:

- **Tool**: `@tools/nx-codegen-json-schema-to-ts`
- **Problem**: app declares need for a json file in TS
- **Outcome**: tool generated TS saved; end-to-end type safety
- **Example**: `@packages/**/contracts/*.json` -> `generated/**_*.ts`

**Generated Targets**:

- **Tool**: `@tools/nx-orchestrate-configurations`
- **Problem**: app declares dynamic targets in `project-targets.json`
- **Outcome**: app default target treated as base for generated configurations

**Auth Tokens**:

- **Tool**: `@tools/nx-generate-auth-token`
- **Problem**: apps have to authenticate to communicate
- **Resolve**: tool returns the new generated token ony
- **Outcome**: app saves it with `nx run-command`; uses it

**Provider Tokens**:

- **Tool**: `@tools/nx-obtain-{provider}-token` - POSTPONED
- **Problem**: setting up provider access tokens is tedious
- **Resolve**: tool creates token with cli and returns it
- **Outcome**: app saves with `nx run-command`; uses it

**Distributed Env**:

- **Tool**: `@tools/nx-distribute-env-variables`
- **Problem**: app needs `SERVICE_TOKEN` of `router-krea2`
- **Outcome**: consumers access `process.env.ROUTER_KREA2_SERVICE_TOKEN`

**Dynamic Urls**:

- **Tool**: `@tools/nx-distribute-resolved-url`
- **Problem**: an app needs to access `APP_URL` of `tmail`
- **Resolve**: dep declared; tool resolves `APP_URL` artifact
- **Outcome**: consumers can access `process.env.TMAIL_APP_URL`

**Enforced Env**: POSRTPONED. DO NOT DO.

- **Tool**: `@tools/nx-enforce-env-variables` + `zod`
- **Problem**: guesses + lack of validation makes `.env` drift
- **Resolve**: apps must declare `{projectRoot}/env.schema.ts`
- **Outcome**: `.env` validated; `schema` now serves as example

**Audit Env**:

- **Tool**: `@tools/nx-audit-env-variables`
- **Problem**: need to verify .env values across the repo
- **Outcome**: outputs a grouped checklist, with masked values

**Verification**:

- **Tool**: `verify`
- **Problem**: need tiered verification after changes
- **Resolve**: `audit` -> `build` -> `test`

---

## Workers

**Role**: cloud GPU inference workers.

- [Workers](./apps/WORKERS.md)

---

## Routers

**Role**: mediate requests between UI and best provider for request.

**[Router](./apps/router/AGENTS.md) targets**:

- **router**:
  - 🫷🏻not served; used only as base for dynamic targets

- **router-flux2:dev**: depends on `worker-flux2:deploy-modal`
- **router-flux2:deploy**: depends on `worker-flux2:deploy-model`

- **router-krea2:dev**: depends on `worker-krea2:dev-modal`
- **router-krea2:deploy**: depends on `worker-krea2:deploy-modal`

---

## Frontends

**Role**: UIs to interact with cloud inference.

**[Generative UI](./apps/generative-ui/AGENTS.md) targets**:

- **generative-ui**:
  - 🫷🏻not served; used only as base for dynamic targets

- **face-value:dev**: depends on `router-flux2:dev`
- **face-value:deploy**: depends on `router-flux2:deploy`
