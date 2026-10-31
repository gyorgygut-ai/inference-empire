# Inference Empire

**Value Proposition**: Monorepo for inference workers + frontends + tooling.

---

## Non-negotiables

**Secrets**: 

- **Env Vars**: `nx` always injects required secrets from `.env*`
- **Schemas**: `@packages/schemas` describes `env` var names to use

**Config**:

- **Runtime**: `dotenvx run -f env.runtime --` injects fresh-generated config values
- **Debug**: `dotenvx run -f env.debug --` injects constant runtime config values
- **Rule** use `env.debug` to debug with constant values; otherwise use `env.runtime`

**Correct**:

- **Goal**: Spec adherence across the codebase without gaps
- **Approach**: Code matched to authoritive specs; NOT specs to code
- **Outcome**: Code fulfilling acceptance criteria as specs dictate

**Proven**:

- **Goal**: Idiomatic, documented patterns instead of hand-rolling and guesses
- **Approach**: Use the `nx-*`, `python-uv` skills and the `nx mcp` to verify
- **Outcome**: Trial-and-error loops eliminated; simple, reliable codebase

---

## Orchestration

**Key Apps**:

  - **GPU Workers**: [Workers](./apps/workers/AGENTS.md)
  - **Multi-tenant Router**: [Router](./apps/router/AGENTS.md)
  - **Face Value Frontend**: [Face Value](./apps/face-value/AGENTS.md)

**Dev URLs**:

- **Problem**: I want to delegate `dev` urls
- **Approach**: 
  - `producer` declares `readyWhen`, `"url": "*:{env.PRODUCER_PORT}"`
  - `consumer` declares it depends on `producer` + `"waitFor": "ready"`
- **Outcome**:
  - `consumer` starts with interpolated `PRODUCER_URL`

**Deploy URLs**:

- **Problem**: I want to delegate `deploy` urls
- **Approach**: 
  - `producer:deploy` runs direct `vendor deploy`
  - `consumer:deploy` depends on `producer:deploy`
  - `consumer:deploy` gets `PRODUCER_URL={get-**-url.ts}`
- **Outcome**:
  - `consumer` can send requests to `producer` url

**Dynamic Config**:

- **Problem**: I want dynamic values generated on each run
- **Approach**: 
  - `config.{dev|deploy}` generates `{GENERATED_TOKEN}`
  - `dotenv-expand` `1000.0.0` enables command substitution
- **Outcome**:
  - `producer` accesses `AUTH_TOKEN={GENERATED_TOKEN}`
  - `consumer` accesses `AUTH_TOKEN={GENERATED_TOKEN}`
  - `consumer` can authenticate itself to `producer`

**Config Delegation**:

- **Problem**: I want to delegate `dev` + `deploy` config
- **Approach**: 
  - tracked `env.runtime` holds shared mandatory runtime config for dev + deploy
  - `options.{env|args}` instead of one-by-one env plumbing
  - `dotenvx/run-commands` supports `options.env` interpolation
  - `.env*`, ids, urls, tokens all treated as secret; gitignored
  - `dotenvx run -f env.runtime --` ensures consistent env
- **Acceptance**:
  - `workflows/deploy.yml`, `gh secrets` kept in sync
  - Untracked `.env*` at `{workspaceRoot}` + `{projectRoot}`
  - Tracked JSON Schema source contracts live in
    `packages/schemas/env/` and `packages/schemas/workers/`
  - Generated TypeScript contracts are outputs; do not edit them by hand
  - Tracked `env.runtime` at `{workspaceRoot}`

---

## Acceptance Criteria

**Task**: `face-value:dev`

- ping `get-beam-url.ts(workers-flux2)` suceeds
- ping `http://127.0.0.1:${DEV_ROUTER_FLUX2_PORT}` suceeds
- ping `http://127.0.0.1:${DEV_FACE_VALUE_PORT}` suceeds

**Task**: `face-value:deploy`

- ping `get-beam-url.ts(workers-flux2)` suceeds
- ping `get-cf-worker-url.ts(router_flux2)` suceeds
  - POST `get-cf-worker-url.ts(router_flux2)/q` + `invalid token`
    -> rejects
  - POST `get-cf-worker-url.ts(router_flux2)/q` + `GENERATED_ROUTER_FLUX2_AUTH_TOKEN`
    -> produces `presigned_url`
- ping `get-vercel-url.ts(SECRET_FACE_VALUE_VERCEL_PROJECT_ID)` suceeds

**Task**: `voice-chat:dev`

- ping `get-beam-url.ts(workers-voice)` suceeds
- ping `http://127.0.0.1:${DEV_VOICE_CHAT_PORT}` suceeds

**Task**: `voice-chat:deploy`

- ping `get-beam-url.ts(workers-voice)` suceeds
- ping `get-vercel-url.ts(SECRET_VOICE_CHAT_VERCEL_PROJECT_ID)` suceeds

---

## Verification

**Rules**:

- **Proof**: the verification chain must prove the implementation
- **Progress**: tier-by-tier; until each tier passes or a failure
- **Failures**: `lint-fix`; report; read logs; investigate; fix; restart
- **Readiness**: assert after `finite` deps or `continuous` ready
- **Tidiness**: max. 6 lines per test case: `setup`->`act`->`assert`

**💪🏾 Full Chain**: `verify`

-> `npx nx run-many -t verify --nxBail`
-> runs `Tier 1` gates `Tier 2` gates `Tier 3`

**🧐 Tier 1: audit**:

-> **dependsOn**: `["lint", "build", "test-unit"]`

**🏡 Tier 2: dev**:

-> **test:acceptance:dev**: `./tools/test/acceptance.dev.test.ts`
-> **test:acceptance:dev-tinysd**: `./tools/test/acceptance.dev-tinysd.test.ts`

**🏰 Tier 3: deploy**:

-> **test:acceptance:deploy**: `./tools/test/acceptance.deploy.test.ts`
