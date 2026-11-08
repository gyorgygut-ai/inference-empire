# Inference Empire

**Value Proposition**: Monorepo for inference workers + frontends + tooling.

---

## Non-negotiables

**Correctness**:

- **Goal**: Spec adherence across the codebase without gaps
- **Approach**: Code matched to authoritive specs; NOT specs to code
- **Outcome**: Code fulfilling acceptance criteria as specs dictate

**Minimalism**:

- **Goal**: Idiomatic, documented patterns instead of hand-rolling and guesses
- **Approach**: Use the `nx-*`, `python-uv` skills and the `nx mcp` to verify
- **Outcome**: Trial-and-error loops eliminated; simple, reliable codebase

**Secrets**:

- **Problem**: Tasks need environment variables, while keeping sensitive values protected
- **Approach**:
  - dotenvx encrypted environment vars in tracked root `.env`
  - Read the key in `.env.local` for seamless use
  - Keep the `decryption key`, `.env.{keys|local}` uncommitted
  - Use `dotenvx set KEY value` to mutate encrypted values
  - Use `@packages/schemas` for environment variable names
- **Outcome**:
  - Nx injects required values from the root `.env`
  - Environment variable names follow shared schema

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

**Config Delegation**:

- **Problem**: I want to delegate `dev` + `deploy` config
- **Approach**: 
  - tracked root `.env` holds shared mandatory runtime config for dev + deploy
  - `options.{env|args}` instead of one-by-one env plumbing
  - `dotenvx/run-commands` supports `options.env` interpolation
  - plaintext config and encrypted credentials coexist in `.env`
  - `.env.keys` and local `.env*` files are untracked
  - Nx loads root `.env` and decrypts encrypted values for task processes
- **Acceptance**:
  - `workflows/deploy.yml` receives `DOTENV_PRIVATE_KEY` from GitHub secrets
  - tracked `.env` at `{workspaceRoot}`; decryption keys remain outside Git
  - untracked app-local `.env*` files
  - Tracked JSON Schema source contracts live in
    `packages/schemas/env/` and `packages/schemas/workers/`
  - Generated TypeScript contracts are outputs; do not edit them by hand

---

## Acceptance Criteria

**Task**: `face-value:dev`

- ping `get-beam-url.ts(worker-flux2)` suceeds
- ping `http://127.0.0.1:${DEV_ROUTER_FLUX2_PORT}` suceeds
- ping `http://127.0.0.1:${DEV_FACE_VALUE_PORT}` suceeds

**Task**: `face-value:deploy`

- ping `get-beam-url.ts(worker-flux2)` suceeds
- ping `get-cf-worker-url.ts(router_flux2)` suceeds
  - POST `get-cf-worker-url.ts(router_flux2)/q` + `invalid token`
    -> rejects
  - POST `get-cf-worker-url.ts(router_flux2)/q` + `ROUTER_FLUX2_AUTH_TOKEN`
    -> produces `presigned_url`
- ping `get-vercel-url.ts(SECRET_FACE_VALUE_VERCEL_PROJECT_ID)` suceeds

**Task**: `voice-chat:dev`

- ping `get-beam-url.ts(worker-voice)` suceeds
- ping `http://127.0.0.1:${DEV_VOICE_CHAT_PORT}` suceeds

**Task**: `voice-chat:deploy`

- ping `get-beam-url.ts(worker-voice)` suceeds
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
