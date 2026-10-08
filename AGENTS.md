# Inference Empire

**Value Proposition**: Monorepo for inference workers, tooling and whitelabel frontends.

---

**Architecture**:

- `GPU worker contracts` sharing boilerplate across multiple providers
- `Dedicated worker routers` routing to best fit provider to serve request
- `Whitelabel frontends` providing UI for requesting inference via routers

**Replicability**:

- `Providers of a contract` are 1 app, with per provider deploy targets
- `Router deploy targets` with each routing to >= 1 `gpu worker` targets
- `Frontend deploy targets` with each routing to >= `gpu worker` targets

---

**Hosting**:

- `GPU workers` on `Beam`, `Modal`, ~~`Flash` (currently disabled)~~
- `Routers` on `Cloudflare Workers` or `Koyeb`
- `Frontends`: NextJS on `Vercel` or `Cloudflare Workers`

**Budget**:

- Use the cheapest viable GPU config for the job
- Use the cheapest hosting option, always prefer free
- Verify locally to avoid cloud GPU costs, except `e2e`

---

**Goals**:

- [x] Cheap, serverless, scale-to-0 gpu workers with fast cold start
- [x] Always accessible text, vision LLMs, Flux 2 + Krea 2 image generation
- [ ] H3 video generation, realtime voice chat + reference voices
- [ ] Easy tooling: inference reqs from cli + Apple Shortcuts
- [ ] Guided Flux 2: Face Value app
- [ ] Reference LLM: Chat UI app
- [ ] Realtime Voice: Realtime Voice app
- [ ] Image + Video: Media Studio app
- [ ] Hassle-free nx generators for new gpu workers
- [ ] Hassle-free nx generators for new frontends
- [ ] Hassle-free nx generators for new routers

---

## Context: Frontends

**Apps**:

- [Chat UI](./apps/chat-ui/AGENTS.md)
- [Face Value](./apps/face-value/AGENTS.md)

**Activate**:

- `.agents/skills/tanstack-ai`

---

## Context: Routers

**Apps**:

- [Worker Router](./apps/worker-router/AGENTS.md)

**Activate**:

- `~/.agents/skills/wrangler`

---

## Context: GPU Workers

**Apps**:

- [Flux2](./apps/flux2/AGENTS.md)
- [Krea2](./apps/krea2/AGENTS.md)
- [TinySD](./apps/tiny_sd/AGENTS.md)
- [Vision](./apps/vision/AGENTS.md)
- [H3 COMFY](./apps/h3_comfy/AGENTS.md)
- [H3 FL2VA](./apps/h3_fl2va/AGENTS.md)
- [H3 REF3VA](./apps/h3_ref2va/AGENTS.md)
- [RT Voice](./apps/realtime_voice/AGENTS.md)

**Activate**:

- `.agents/skills/modal`
- `~/.agents/skills/python-uv`
- `~/.agents/skills/cloud-gpu-workers`

**Structure**:

- Naming pattern: `worker_{platform}_{pattern}_{model}.py`
- Contracts: in `packages/{model}/contract.json` with `input` + `output`
- Typing: consumers generate types and `Pydantic` generates models from `contract json`

**Provider Config**:

- Max. 1 worker, scale to 0, short idle timeouts, (`workers=(0, 1)`)
- Use `flashboot=True`, `model cache` for quick starts
- Use `Volume` (`./hf-cache`) if provider doesn't do built-in cache
- Models lazy downloaded and cached on first request, `tools/seed-volumes` allowed

**Business Logic**:

- Proxy: ~~GRPC + queue proxy in each worker~~ goal: handled by routers
- Queue: non-realtime workers use the task queue, returning pollable task id
- Artifacts: if it generates a file, it should produce an artifact, use `packages/shared-gpu/artifacts`
- Sharing: thin minimal wrappers around providers, business logic shared via `packages/{model}|shared-gpu`

**Testing Strategy**

- Rule: value over volume. each test must prove a specced requirement.
- Unit: assert output + artifact for a given input (bad, good), stub side effects
- Working stubs: avoid mocking. rely instead on real stubs + DI to test side effects
- E2E: sole sunny test case per worker asserting output and artifacts, do not stub

---

## E2E Tests

- Good input: should return contract + artifact must exist in bucket (if applicable)

**Acceptance Criteria**:

- 100% job: no shortcuts, no skimming. static analysis results must always be kept error-free
- Static tools: `lint`, `ruff`, `dep check`, `imports`, `dead code analysis`, `syntax validation`
- Prove what's possible locally. avoid coding-deploy-fail-fix-rinse-repeat loops
- Avoid guessing. Provider `deploy logs or worker logs` accessible for error tracking

---

## Context: NX Workspace Management

**Activate**:

- `.opencode/skills/nx-workspace`

**Orchestration**:

- Router deploys depend on specific workers, frontends on routers
- Deploy order: consumers always last, `gpu workers` -> `routers` -> `frontends`
- Authentication: `apps` emit `tokens` as `deploy output`, `frontends` consume them
- Secret tokens: `frontends` http reqs `proxied` or by `ephemeral tokens` issued `server-side`

**Correctness**:

- `gpu worker` provider parity enforced via minimal thin provider code and shared packages
- `nx graph` maintained so that it always deploys with correct dependency graph, idempotently

**Sharing**:

- `ui apps` examples: `packages/shared-ui`, `packages/shared-ui/worker-router-client`
- `gpu worker` examples: `packages/shared-gpu`, `packages/shared-gpu/storage`, `packages/flux2`

**Tooling**:

- `nx generators` examples: quick scaffolding of new workers, routers, uis
- `nx executors` examples: `tests`, `gpu verification`, `sandboxed e2e`, `static analysis`

**Workflow**:

- Tiers: `static` -> `dep check` -> `unit` -> `e2e` -> `deploy`
- Tiers verified progressively; NO `e2e`, nor `deploy` until proven
- Maintenance requirement strictly in place even if a path is disabled
- Local deploy: `npm run deploy`; CI/CD: nx affected + static, unit tests
