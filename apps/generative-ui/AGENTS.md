# Generative UI

NextJS app for chat + inference requests.

**Non-negotiables**:

- USE `@tanstack/ai/*`; utilize the library fully
- NO hand-rolled ui; NO state management; `@tanstack/ai` does it
- NO `useEffect`, `useState`; state travels through tools
- NO multiple components per file; NO `deprecated` component usage
- NO inline component customization in chat config; extract it
- DO let TS infer types; NO `any`, NO `as`; NO `lib|helpers|util`
- NO auth tokens or other secrets exposed to the browser
- Message and approval state transitions go through the chat library's APIs — never hand-appended parts or hand-matched state strings

---

## Target: Face Value

Progressive chat thread, with NO LLM: tool result triggres next tool call.

**target:generate-ts**:

- **inputs**: `{workspaceRoot}/apps/router/dist/flux2_api.json`
- **outputs**: `{projectRoot}/generated/router_flux2_api.ts`
- **dependsOn**: `router:router-flux2-generate-api`
- **cache**: true

**NX Project**:

- Project `generative-ui`, target `face-value`, `executor: nx:run-commands`, `defaultConfiguration: dev`, `cache: false`, `continuous: true`
- `configurations: { dev: { command, envFile }, deploy: { command, envFile } }`
- `dependsOn: [{ projects: [router], target: router-flux2, configuration: matched }, face-value-setup, face-value-generate-ts]`

**target:face-value-setup**:

- **inputs**: `dist/router/{dev|deploy}/router-flux2.env`
- **outputs**: `dist/generative-ui/{dev|deploy}/face-value.env`
- **command**: `ENVS=$(tsx tools/orchestration/prefix-env-vars.ts dist/router/{dev|deploy}/router-flux2.env ROUTER_FLUX2)` plus `tsx tools/orchestration/upsert-artifact.ts generative-ui {dev|deploy} face-value $ENVS`

**Environment**:

- Loaded via `envFile: dist/generative-ui/{dev|deploy}/face-value.env` in `configurations`, never via runtime parsing
- `ROUTER_FLUX2_APP_URL` plus `ROUTER_FLUX2_SECRET_AUTH_TOKEN` copied from router artifact by `face-value-setup` on `dev` plus `deploy`

**Outcomes**:

- `./targets/face-value/outcomes/`: one `.md` per outcome, frontmatter (`id`, `title`, `order`, `width`, `height`), body never exposed to browser

**Inference Requests**:

- Url: `ROUTER_FLUX2_APP_URL` from env
- Auth: `ROUTER_FLUX2_SECRET_AUTH_TOKEN` from env
- Client: `packages/task-queue-client` (`POST /q`, `GET /sup`)
- Action: `./app/actions/generate-image`; returns `error` OR `presignedUrl`
- Reference image validated and resized to max. 512×512 on server

**Flow**: `requestSelectedOutcome` -> `requestReferenceImage` -> `runGenerateImage`

- Trigger: initial assistant message, Tool: `presentOutcomeOptions`
- Trigger: outcome result, Tool: `presentImageUpload`
- Trigger: image result, Tool: `runGenerateImage` (needs approval, renders `<GenerateImageTool />`)
