# Generative UI

NextJS app for chat + inference requests.

---

## UI Shell

**Layout**:

- `./app/page.tsx`: only `SplitLayout`
- `./shell/SplitLayout.tsx`:
  - default: full width `chat/Client`
  - from md: 2/3 `aside > HeroImage` + 1/3 `chat/Client`
- `./shell/HeroImage.tsx`: hero image fills space

**Chat**:

- `./chat/client.tsx`: `chat.AppChat`
- `./chat/options.ts`: chat ui `options`
- `./chat/components/`: chat ui `components`

- `./chat/options/`: a `chatOption` per file
- `./chat/messages/`: a `message factory` per file

- `./chat/parts/{.ts}`: a `part factory` per file
- `./chat/parts/components/`: `partsComponents`, one per file

- `./chat/tools/`: a tool per file, `toolDefinition` + `schema`
- `./chat/tools/components/`: `toolsComponents`, one per file

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

- **input**: `@apps/router/dist/router_flux2_api.json`
- **output**: generated TS, `generated/router_flux2_api.ts`

**Environment**:

- `ROUTER_FLUX2_APP_URL` resolved on `dev` + `deploy`
- `ROUTER_FLUX2_SECRET_AUTH_TOKEN`: re-generated on `build`

**Vocabulary**:

- `./targets/face-value/vocabulary/`: `en` (default)

**Outcomes**:

- `./targets/face-value/outcomes/`: one `.md` per outcome
- frontmatter: (`id`, `title`, `order`, `width`, `height`);
- prompt: markdown body, can never be exposed to browser

**Inference Requests**:

- Url: `ROUTER_FLUX2_APP_URL` from env
- Auth: `ROUTER_FLUX2_SECRET_AUTH_TOKEN` from env
- Client: use `packages/task-queue-client` (`POST /q`, `GET /sup`) to send requests
- Action: `./app/actions/generate-image`; returns `error` OR `presignedUrl`
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
  - states render in `<GenerateImageTool />`
  - awaiting-input+input-streaming: `<Spinner />`
  - approval-requested: `<GenerateImageApproval />` — approve prompt via the
    chat library's approval flow (text: `runGenerateImage.requested.assistantMessage`,
    button: `runGenerateImage.requested.userApprove`)
  - approval-responded: text `runGenerateImage.responded.assistantMessage`
  - during generation: text `runGenerateImage.streaming.assistantMessage`
  - error: text `runGenerateImage.error.assistantMessage`
  - complete: `<GenerateImageArtifact src={presigned url} />`
