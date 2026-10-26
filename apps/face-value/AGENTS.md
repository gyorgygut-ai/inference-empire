# Face Value

NextJS app for chat + inference requests.

---

## NX: `face-value`

**Tasks**:

- `dev`:
  - command: [
    ROUTER_URL=$NX_READY_URL,
    ROUTER_AUTH_TOKEN=$ROUTER_GENERATED_AUTH_TOKEN,
    next dev
  ]
  - dependsOn:
    ```json
    [
      "predev",
      {
        "projects": ["functions"],
        "target": "dev",
        "waitFor": "ready"
      }
    ]
    ```
  - Router dependency uses `functions:dev`'s default configuration, `flux2`
  - inputs: "{workspaceRoot}/packages/contracts/task-queue-service/flux2-dev.contract.ts"
- `predev`, `prebuild`:
  - dependsOn `^prebuild`
- `build`:
  - dependsOn `prebuild`
- `deploy`:
  - command: [
    ROUTER_URL=$ROUTER_RESOLVED_URL,
    ROUTER_AUTH_TOKEN=$ROUTER_GENERATED_AUTH_TOKEN,
    vercel deploy --token={options.token} --orgId=... --projectId=...
  ]
  - options: { token: "env.FACE_VALUE_VERCEL_TOKEN", orgId, projectId }
  - dependsOn `["build", "functions:deploy:flux2"]`
  - inputs: "{workspaceRoot}/packages/contracts/task-queue-service/flux2-deploy.contract.ts"

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

- Url: `TaskQueueServiceContract.ROUTER_RESOLVED_URL`
- Auth: `TaskQueueServiceContract.ROUTER_GENERATED_AUTH_TOKEN`
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
