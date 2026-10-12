# Inference Empire

**Value Proposition**: Monorepo for inference workers + frontends + tooling.

- **ACTIVATE**: `./opencode/skills/nx-workspace`
- **Paths**: assume `{projectRoot}` in relative paths
- **Specs**: specs are always authoritive. Code must match specs
- **NON-gaps**: good code without specs, example names not coded

---

## Monorepo Orchestration

**Dependence order**:

- **Tool**: `dependsOn plus configurations`
- **Problem**: consumers start before producers are ready
- **Resolve**: consumer sets `dependsOn` with matched `configuration`
- **Outcome**: one run boots full chain

**Variant configurations**:

- **Tool**: `targets.configurations`
- **Problem**: one project serves many variants
- **Resolve**: one target per variant, each with `dev`, `deploy` entries holding `command` plus `envFile`
- **Outcome**: target picks variant, configuration picks mode

**Env artifact contract**:

- **Tool**: `outputs plus envFile`
- **Problem**: runtime values must flow between targets
- **Resolve**: producer declares `outputs` plus writes file, consumer declares `envFile` in matched entry
- **Outcome**: cacheable handoff
- **Ban**: zero runtime dotenv parsing

**Uniform deploy / start scripts**:

- **Tool**: `tools/deploy-vercel|modal|beam|flash plus tools/start-next|modal|beam|flash`
- **Problem**: each provider needs identical deploy plus start behavior
- **Resolve**: script inputs `project, configuration, target`, writes `APP_URL` to contracted path
- **Outcome**: all listed providers share one write contract

**Orchestration primitives**:

- **Tool**: `tools/orchestration/*` single-file `tsx`, zero executors, zero plugins
- **Problem**: env file writes scattered across app scripts
- **Resolve**: only `upsert-artifact.ts` writes files, others print to stdout for composition
- **Outcome**: one writer, composable one-liners in `project.json`

**Contracts**:

- `generate-auth-token.ts` — zero args, stdout `<token>`, zero file IO
- `prefix-env-vars.ts` — args `<src-file> <PREFIX>`, stdout `PREFIX_KEY=VAL` lines, zero file IO
- `upsert-artifact.ts` — args `<project> <configuration> <target> KEY=VAL...`, upserts into `dist/{project}/{configuration}/{target}.env`, sole `mkdirSync` plus `writeFileSync` owner

**Verification**:

- **Tool**: `verify`
- **Problem**: need tiered verification after changes
- **Resolve**: `audit` -> `build` -> `test`

---

## Workers

**Role**: cloud GPU inference workers.

- [Workers](./apps/WORKERS.md)
- e.g. `worker-flux2:deploy-modal`, artifact `dist/worker-flux2/deploy/deploy-modal.env`, keys `APP_URL`

---

## Routers

**Role**: mediate requests between UI and best provider for request.

- [Router](./apps/router/AGENTS.md)
- e.g. `router:router-flux2 -c dev|deploy`, artifact `dist/router/dev|deploy/router-flux2.env`, keys `APP_URL` plus `SECRET_AUTH_TOKEN`

---

## Frontends

**Role**: UIs to interact with cloud inference.

- [Generative UI](./apps/generative-ui/AGENTS.md)
- e.g. `generative-ui:face-value -c dev|deploy`, artifact `dist/generative-ui/dev|deploy/face-value.env`, keys `ROUTER_FLUX2_APP_URL` plus `ROUTER_FLUX2_SECRET_AUTH_TOKEN`
