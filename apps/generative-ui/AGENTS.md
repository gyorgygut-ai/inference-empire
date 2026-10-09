# Generative UI Agent Specs

**Project goal**:
NextJS app for chat + inference requests.

## NextJS non-negotiables

- **Server Components**: static shell, outcome prompts server-only. [Server and Client Components](https://nextjs.org/docs/app/getting-started/server-and-client-components)
- **Server Actions**: reference image submit + Flux call, no API routes. [Server Actions and Mutations](https://nextjs.org/docs/app/building-your-application/data-fetching/server-actions-and-mutations)
- **React Compiler**: no manual memoization. [React Compiler](https://react.dev/learn/react-compiler)

---

## UI Flow (Flow-agnostic shell)

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

- `./chat/adapters/`: an `adapter` per file
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

---

## UI Flow (Face Value)

Progressive chat thread, with NO LLM: tool result triggres next tool call.

**Vocabulary**:

- `./targets/face-value/vocabulary/`: `en` (default) + `hu`

**Outcomes**:

- `./targets/face-value/outcomes/`: one `.md` per outcome
- fm: (`id`, `title`, `order`, `width`, `height`);
- prompt: markdown body, can never be exposed to browser

**Inference Requests**:

- Url: `GENERATE_IMAGE_SERVICE_URL` from env
- Auth: `GENERATE_IMAGE_SERVICE_SECRET_AUTH_TOKEN` from env
- Client: use `packages/worker-router-client` to send requests
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
