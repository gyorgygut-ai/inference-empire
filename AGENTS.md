# Inference Empire

**Value Proposition**: Monorepo for inference workers + frontends + tooling.

- **ACTIVATE**: `./opencode/skills/nx-workspace`
- **Paths**: assume `{projectRoot}` in relative paths
- **Specs**: specs are always authoritive. Code must match specs
- **NON-gaps**: good code without specs, example names not coded

---

## Monorepo Orchestration

> One tool per job tells the story clearly.
> DO NOT stuff everything into workspace-plugin.

**Generated Types**:

- **Tool**: `@tools/nx-codegen-json-schema-to-ts`
- **Problem**: app declares dep on a contract schema
- **Outcome**: end-to-end type safety; `generated/{target}_contract.ts`

**Generated Targets**:

- **Tool**: `@tools/nx-orchestrate-configurations`
- **Problem**: app declares dynamic targets in `project-targets.json`
- **Outcome**: app default target treated as base, configurations generated

**Distributed Env**:

- **Tool**: `@tools/nx-distribute-env-variables`
- **Problem**: app needs `THAT_VAR` of `{dep-project}:{target}`
- **Outcome**: consumers can use emitted `DEP_PROJECT_THAT_VAR`

**Dynamic Urls**:

- **Tool**: `@tools/nx-distribute-resolved-url`
- **Problem**: `{dep-project}` url unknown before `:{target}`
- **Resolve**: dependency declared; `APP_URL` output resolved
- **Outcome**: consumers can now contact `DEP_PROJECT_APP_URL`

**Enforced Env**:

- **Tool**: `@tools/nx-enforce-env-variables` + `zod`
- **Problem**: guesses + lack of validation makes `.env` drift
- **Resolve**: apps must declare `{projectRoot}/env.schema.ts`
- **Outcome**: `.env` validated; `schema` now serves as example

**Audit Env**:

- **Tool**: `@tools/nx-audit-env-variables`
- **Problem**: need to verify .env values across the repo
- **Outcome**: outputs a grouped checklist, with masked values

**Auth Tokens**:

- **Tool**: `@tools/nx-generate-auth-token`
- **Problem**: apps have to authenticate to communicate
- **Resolve**: apps output `SECRET_AUTH_TOKEN` as needed
- **Outcome**: consumers send auth header; request validated

**Provider Tokens**:

- **Tool**: `@tools/nx-obtain-{provider}-token`
- **Problem**: setting up provider access tokens is tedious
- **Resolve**: creates token using respective provider cli
- **Outcome**: token wired into selected project + `gh secrets`,

**Static Verification**:

- **Tool**: `verify`
- **Problem**: need tiered verification after changes
- **Resolve**: `audit` -> `lint` -> `build` -> `test`

**Dev Verification**:

- **Tool**: `verify-dev`
- **Problem**: need to verify end-to-end orchestration
- **Resolve**: `audit` -> `lint` -> `build` -> `test-unit` -> `dev`

**Deploy Verification**:

- **Tool**: `verify-deploy`
- **Problem**: need to verify end-to-end orchestration + deploy
- **Resolve**: `audit` -> `lint` -> `build` -> `test` -> `deploy`

---

## Workers

**Role**: cloud GPU inference workers.

- [Workers](./apps/workers/AGENTS.md)

---

## Routers

**Role**: mediate requests between UI and best provider for request.

**[Router](./apps/router/AGENTS.md) targets**:

- [ ] `router-flux2` 👈🏾 👉🏼 `worker-flux2`:`dev,deploy`
- [ ] `router-krea2` 👈🏾 👉🏼 `worker-krea2`:`dev-modal,deploy-modal`

---

## Frontends

**Role**: UIs to interact with cloud inference.

**[Generative UI](./apps/generative-ui/AGENTS.md) targets**:

- [ ] `face-value` 👈🏾 👉🏼 `router-flux2`:`dev,deploy`
