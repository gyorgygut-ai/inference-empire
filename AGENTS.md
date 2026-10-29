# Inference Empire

**Value Proposition**: Monorepo for inference workers + frontends + tooling.

---

## Non-negotiables

**Config**: Use `dotenvx run -f config.{dev|deploy} --` for `nx` if config is needed

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
  - **Multi-tenant Router**: [Router](./apps/functions/AGENTS.md)
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

**Env Delegation**:

- **Problem**: I want to delegate `dev` + `deploy` config
- **Approach**: 
  - `config.{dev|deploy}` holds mandatory runtime config
  - `options.{env|args}` instead of one-by-one env plumbing
  - `dotenvx/run-commands` supports `options.env` interpolation
  - `.env*`, ids, urls, tokens all treated as secret; gitignored
  - `dotenvx run -f config.{dev|deploy} --` ensures consistent env
- **Acceptance**:
  - `workflows/deploy.yml`, `gh secrets` kept in sync
  - Untracked `.env*` at `{workspaceRoot}` + `{projectRoot}`
  - Tracked `env*.{example|schema.ts}` for each `.env*` file
  - Tracked `config.dev` + `config.deploy` at `{workspaceRoot}`

---

## Acceptance Criteria

**Task**: `functions:dev`

- PING `{get-beam-url.ts(workers-flux2)}` suceeds
- PING `{get-beam-url.ts(workers-tinysd)}` suceeds
- POST `:${ROUTER_FLUX2_PORT}/q` + `ROUTER_FLUX2_GENERATED_AUTH_TOKEN`
  -> produces a `flux2` `presigned_url`
- POST `:${ROUTER_TINYSD_PORT}/q` + `ROUTER_FLUX2_GENERATED_AUTH_TOKEN`
  -> rejects the token
- POST `:${ROUTER_tinysd_PORT}/q` + `ROUTER_TINYSD_GENERATED_AUTH_TOKEN`
  -> produces a `tinysd` `presigned_url`

**Task**: `functions:deploy`

- PING `{get-beam-url.ts(workers-flux2)}` suceeds
- PING `{get-beam-url.ts(workers-tinysd)}` suceeds
- POST `get-cf-worker-url.ts(router_flux2)/q` + `ROUTER_FLUX2_GENERATED_AUTH_TOKEN`
  -> produces a `flux2` `presigned_url`
- POST `get-cf-worker-url.ts(router_flux2)/q` + `ROUTER_TINYSD_GENERATED_AUTH_TOKEN`
  -> rejects the token
- POST `get-cf-worker-url.ts(router_tinysd)/q` + `ROUTER_TINYSD_GENERATED_AUTH_TOKEN`
  -> produces a `tinysd` `presigned_url`

**Task**: `face-value:dev`

- ping `get-beam-url.ts(workers-flux2)` suceeds
- ping `http://127.0.0.1:${ROUTER_FLUX2_PORT}` suceeds
- ping `http://127.0.0.1:${FACE_VALUE_PORT}` suceeds

**Task**: `face-value:deploy`

- ping `get-beam-url.ts(workers-flux2)` suceeds
- ping `get-cf-worker-url.ts(router_flux2)` suceeds
- ping `get-vercel-url.ts(FACE_VALUE_VERCEL_PROJECT_ID)` suceeds

---

## Verification

**Non-negotiable**:

- **Proof**: the verification chain must prove the implementation
- **Progress**: tier-by-tier; until each tier passes or a failure
- **Failures**: `lint-fix`; report; read logs; investigate; fix; restart
- **Readiness**: assert after `finite` deps or `continuous` ready
- **Tidiness**: max. 6 lines per test case: `setup`->`act`->`assert`

**💪🏾 Full Chain**: `verify`

-> `npx nx run-many -t verify --nxBail`
-> runs `verify-tier-1` gates `verify-tier-2` gates `verify-tier-3`

**🧐 Tier 1: audit**: `verify-tier-1-audit` 

-> **dependsOn**: `["lint", "build", "test-unit"]`

**🏡 Tier 2: dev**: `verify-tier-2-dev`

-> **dependsOn**: `["verify-tier-1*", "acceptance:dev*", "e2e:dev*"]`
-> **test:acceptance:dev**: `./tools/test/acceptance.dev.test.ts`
-> **test:acceptance:dev-tinysd**: `./tools/test/acceptance.dev-tinysd.test.ts`
-> **test:e2e:dev**: `nx:no-op`

**🏰 Tier 3: deploy**: `verify-tier-3-deploy`

-> **dependsOn**: `["verify-tier-2*", "acceptance:deploy*", "e2e:deploy*"]`
-> **test:acceptance:deploy**: `./tools/test/acceptance.deploy.test.ts`
-> **test:e2e:deploy**: `nx:no-op`
