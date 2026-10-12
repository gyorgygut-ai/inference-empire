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

---

## NX target: `face-value:(dev|deploy)`

**:dev**:

- **depends**: `router-flux2:dev-modal`
- **envFile**: `@dist/router-flux2/dev.env`

**:deploy**:

- **depends**: `router-flux2:deploy-modal`
- **command**: `@tools/deploy-vercel`
- **envFile**: `@dist/router-flux2/deploy.env`

**target:generate-ts**:

- **command**: `run-commands` `./scripts/generate-ts`
- **input: api**: `@dist/router/{dev|deploy}/router-flux2-api.json`
- **output + artifact**: `./generated/router-api.ts`

**Outcomes**:

- `./targets/face-value/outcomes/`: one `.md` per outcome, frontmatter (`id`, `title`, `order`, `width`, `height`), body never exposed to browser

**Inference Requests**:

- Url: `ROUTER_URL` from env
- Auth: `SECRET_AUTH_TOKEN` from env
- Client: `packages/task-queue-client` (`POST /q`, `GET /sup`)
- Action: `./app/actions/generate-image`; returns `error` OR `presignedUrl`
- Reference image validated and resized to max. 512×512 on server

**Flow**: `requestSelectedOutcome` -> `requestReferenceImage` -> `runGenerateImage`

- Trigger: initial assistant message, Tool: `presentOutcomeOptions`
- Trigger: outcome result, Tool: `presentImageUpload`
- Trigger: image result, Tool: `runGenerateImage` (needs approval, renders `<GenerateImageTool />`)
