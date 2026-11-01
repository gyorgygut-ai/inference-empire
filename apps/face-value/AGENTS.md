# Face Value

NextJS app for chat + inference requests.

---

## Dev ENV

**env**:
  - `PORT`: `${DEV_FACE_VALUE_PORT}`
  - `ROUTER_URL`: `http://localhost:${DEV_ROUTER_FLUX2_PORT}`
  - `ROUTER_AUTH_TOKEN`: `${GENERATED_ROUTER_FLUX2_AUTH_TOKEN}`

**NX**:
  - **Cmd**: `next dev` directly
  - **Depends**: `predev`, `router/dev-flux2` + `"waitFor": "ready"`
  - **Types**: `predev` -> `prebuild` -> `^prebuild`

## Deploy ENV

**dotenv**:
  - `ROUTER_AUTH_TOKEN`: `${GENERATED_ROUTER_FLUX2_AUTH_TOKEN}`

**NX**:
  - **Cmd**: `next deploy`, with `SECRET_FACE_VALUE_VERCEL_{TOKEN|ORG_ID|PROJECT_ID}`
  - **Depends**: `build`, `router/deploy-flux2`
  - **Types**: `build` -> `prebuild` -> `^prebuild`
  - **ROUTER_URL**: get directly `get-cf-worker-url.ts(router_flux2)`

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
- `./chat/options.ts`: chat ui `options` (append-only fetcher inline, no LLM transport)
- `./chat/messages/`: a `message factory` per file
- `./chat/parts/`: a `part factory` per file
- `./messages/`: vocabulary entrypoint (re-exports default locale)
- `./chat/vocabulary/`: `en.ts` (default)
- `./outcomes/`: one `.md` per outcome
  - fm: (`id`, `title`, `order`, `width`, `height`);
  - prompt: markdown body, can never be exposed to browser
- `./outcomes/index.ts`: server-only loader (`getPublicOutcomes`, `getInferenceOutcome`)
- `chat/tools/{tool}/`: `{index.ts|definition.ts|components/|results/}`, one fn per file

---

## UI Flow

Progressive chat thread, with NO LLM: tool result triggres next tool call.

**Inference Requests**:

- Url: `ROUTER_URL`
- Auth: `ROUTER_AUTH_TOKEN`
- Client: use `@packages/worker-router-client` to send requests
- Action: `./app/actions/generate-image`, returning `error` OR `presignedUrl`
- Types: TS api types auto-generated (TO BE DISCUSSED)
- Reference image validated and resized to max. 512×512 on server

**No Empty Nodes**:

- **Problem**: `MessageProps.message` has `parts`; empty arrays render empty articles
- **Approach**: `if (!message.parts || message.parts.length === 0) return null` — guard before DOM

**1. Request Selected Outcome**:

- Trigger: initial assistant message
- Text: `requestSelectedOutcome.assistantMessage`
- Tool: `presentOutcomeOptions` -> `title` in 2-col grid; sort by `order`

**2. Request Reference Image**:

- Trigger: `requestSelectedOutcome` result
- Text: `requestReferenceImage.assistantMessage`
- Tool: `presentImageUpload` -> image upload dropzone

**3. Approve + Run Image Generation**:

- Trigger: `requestReferenceImage` result
- Tool: `runGenerateImage` -> two calls of the same tool:
  - call 1 `approval-requested`: `<GenerateImageApproval />`
    - text: `runGenerateImage.requested.assistantMessage`
    - button: `runGenerateImage.requested.userApprove`
  - call 2 `input-complete`: `<Spinner />`
    - text: `runGenerateImage.responded.assistantMessage`
  - error: `runGenerateImage.error.assistantMessage`
  - complete: `<GenerateImageArtifact src={presigned url} />`

<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
