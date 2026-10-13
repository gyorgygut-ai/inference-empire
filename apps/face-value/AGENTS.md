# Face Value

NextJS app for chat + inference requests.

---

## NX target: `face-value:(dev|deploy)`

**:dev**:

- **depends**: `router-flux2:dev`
- **env vars**:
  - any local env handled by nx
  - source `@dist/router-flux2/dev/ROUTER_URL`
  - source `@dist/router-flux2/dev/ROUTER_SECRET_AUTH_TOKEN`

**:deploy**:

- **depends**: `router-flux2:deploy`
- **command**: `@tools/deploy-vercel`
- **env vars**:
  - any local env handled by nx
  - source `@dist/router-flux2/dev/ROUTER_URL`
  - source `@dist/router-flux2/dev/ROUTER_SECRET_AUTH_TOKEN`

**target:generate-ts**:

- **command**: `run-commands` `./scripts/generate-ts`
- **input: api**: `@dist/router/{dev|deploy}/router-flux2-api.json`
- **output + artifact**: `./generated/router-api.ts`

---

## UI Flow (Flow-agnostic shell)

**Non-negotiables**:

- USE `@tanstack/ai/*`; utilize the library fully, no hand-rolling
- NO hand-rolled ui; NO state management; `@tanstack/ai` does it
- NO `useEffect`, `useState`; state travels through tools
- NO multiple components per file; NO `deprecated` component usage
- NO inline component customization in chat config; extract it
- DO let TS infer types; NO `any`, NO `as`; NO `lib|helpers|util`
- NO auth tokens or other secrets exposed to the browser

---

## Structure

**{projectRoot} files**:

- `./app/page.tsx`: only `SplitLayout`
- `./chat/shell/SplitLayout.tsx`:
  - default: full width `chat/Client`
  - from md: 2/3 `aside > HeroImage` + 1/3 `chat/Client`
- `./chat/shell/HeroImage.tsx`: hero image fills space
- `./chat/client.tsx`: `chat.AppChat`
- `./chat/options.ts`: chat ui `options`
- `./chat/adapters/`: an `adapter` per file
- `./chat/options/`: a `chatOption` per file
- `./chat/messages/`: a `message factory` per file
- `./chat/vocabulary/`: `en.ts` (default) + `hu.ts`
- `./outcomes/`: one `.md` per outcome
  - fm: (`id`, `title`, `order`, `width`, `height`);
  - prompt: markdown body, can never be exposed to browser

**Shared @packages/ui/**:

- `chat/components/`: chat ui `components`
- `chat/components/Layout.tsx`
- `chat/components/Message.tsx`
- `chat/parts/{.ts}`: a `part factory` per file
- `chat/parts/components/`: `partsComponents`, one per file
- `chat/tools/`: a tool per file, `toolDefinition` + `schema`
- `chat/tools/runGenerateImage`
- `chat/tools/presentImageUpload`
- `chat/tools/presentOutcomeOptions`
- `chat/tools/components/`: `toolsComponents`, one per file

---

## UI Flow

Progressive chat thread, with NO LLM: tool result triggres next tool call.

**Inference Requests**:

- Url: `env.ROUTER_URL` from env
- Auth: `env.ROUTER_SECRET_AUTH_TOKEN` from env
- Client: use `@packages/worker-router-client` to send requests
- Action: `./app/actions/generate-image`, returning `error` OR `presignedUrl`
- Types: TS api types auto-generated (TO BE DISCUSSED)
- Reference image validated and resized to max. 512×512 on server

**1. Request Selected Outcome**:

- Trigger: initial assistant message
- Text: `requestSelectedOutcome.assistantMessage`
- Tool: `presentOutcomeOptions` -> `title` in 2-col grid; sort by `order`

**2. Request Reference Image**:

- Trigger: `requestSelectedOutcome` result
- Text: `requestReferenceImage.assistantMessage`
- Tool: `presentImageUpload` -> image upload dropzone

**3. Run Image Generation**:

- Trigger: `requestReferenceImage` result
- Tool: `runGenerateImage` -> needs approval
  - awaiting-input+input-streaming: `<Spinner />`
  - approval-requested: `<GenerateImageApproval />`
    - text: `runGenerateImage.requested.assistantMessage`
    - button: `runGenerateImage.requested.userApprove`
  - approval-responded: `runGenerateImage.responded.assistantMessage`
  - error: `runGenerateImage.error.assistantMessage`
  - streaming: `runGenerateImage.streaming.assistantMessage`
  - complete: `<GenerateImageArtifact src={presigned url} />`
