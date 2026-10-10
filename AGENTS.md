# Inference Empire

**ACTIVATE**: `./opencode/skills/nx-workspace`
**Value Proposition**: Monorepo for inference workers, tooling and whitelabel frontends.

**Critical**:

- Names in examples are **made up**
- Assume `{projectRoot}` in relative paths
- Specs: authoritive. Code always matches specs.

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

**Auth Tokens**:

- **Tool**: `@tools/nx-generate-auth-token`
- **Problem**: apps have to authenticate to communicate
- **Resolve**: apps output `SECRET_AUTH_TOKEN` as needed
- **Outcome**: consumers send auth header; request validated

**Provider Tokens**:

- **Tool**: DO NOT start this yet - its a TBD
- **Problem**: generating vercel, cloudflare tokens is a PITA
- **Resolve**:
- **Outcome**:

**Env Verification**:

- **Tool**: DO NOT start this yet - its a TBD
- **Problem**:
- **Outcome**:

**Grap Verification**:

- **Tool**: `verify`
- **Problem**: need verification after changes, in tiers
- **Outcome**: `audit` -> `lint` -> `build` -> `test` -> ✅

**Full Verification**:

- **Tool**: DO NOT start this yet - its a TBD
- **Problem**:
- **Outcome**:

---

## Workers

**Role**: cloud GPU inference workers.

- [Workers](./apps/workers/AGENTS.md)

---

## Routers

**Role**: mediate requests between UI and best provider for request.

- [Router](./apps/router/AGENTS.md)

---

## Frontends

**Role**: UIs to interact with cloud inference.

- [Generative UI](./apps/generative-ui/AGENTS.md)

---

## Examples

**Model Orchestration**:

TODO

**Generated Orchestration**:

TODO

---

## Real Targets

**router-flux2**:

- router

**face-value**:

- generative-ui

<!--- `router`: only a template for generated targets:
  - `router-flux2`: relies on `flux2:dev` + `flux2:deploy`
  - `router-krea2`: relies on `krea2:dev` + `krea2:deploy`

****:

- `generative-ui` is a template for generated targets
  - `face-value`: relies on `router-flux2:dev` + `router-flux2:deploy`
  - `contract`: [Flux2](./packages/contracts/flux2/inference.json)-->
