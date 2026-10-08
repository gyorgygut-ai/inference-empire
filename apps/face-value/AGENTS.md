# Face Value Agent Specs

**Project goal**:
NextJS app demonstrating a selection of NextJS features - most introduced in the last 1.5 years.

## Core User Flow

1. Upload reference image
2. Select an outcome
3. Send inference request
4. Display error / generated image

## NextJS non-negotiables

- **Server Components**: static shell, outcome prompts server-only. [Server and Client Components](https://nextjs.org/docs/app/getting-started/server-and-client-components)
- **Server Actions**: reference image submit + Flux call, no API routes. [Server Actions and Mutations](https://nextjs.org/docs/app/building-your-application/data-fetching/server-actions-and-mutations)
- **React Compiler**: no manual memoization. [React Compiler](https://react.dev/learn/react-compiler)

## Business Logic

- **Magic Encapsulated**:
  - `worker-router-flux2` URL derived from `dist/apps/flux2/contract.json` (`workerUrl`, emitted by `flux2-router:deploy`) at build time via server-only `router-config.ts`, never exposed to client
  - Auth token never written to disk: Cloudflare secret on the worker side, `FLUX2_ROUTER_TOKEN` build env on the face-value side
  - Client sends reference image + selected outcome id upon submit to Server Action
  - Server Action posts outcome prompt + reference image to `worker-router-flux2` `/queue`, polls `/task/:id`
  - Upon response, serves generated image or error message to client
- **Markdown + Frontmatter**:
  - Each outcome is a .md file in /outcomes
  - Frontmatter: (id, title, order, width, height), body = prompt
  - Never exposed to client as is, id and title for display only
- **Proper Data Handling**:
  - Where data is dynamic, the "empty, 1, many data" cases should be handled
  - Same goes for loading, success, error states at the minimum
- **Reference Image Handling**:
  - User uploads their own image
  - Resized to max 512×512 on server before sending to inference server
  - Server validates type, size, format before sending to inference server

**Inference Backend API**

- Contract: `apps/face-value/app/inference-api/schema.ts`
- Polling logic encapsulated in `packages/worker-router-client`
- Send `FLUX2_ROUTER_TOKEN` as auth token
- Action returns `presignedUrl` or `error` to ui
- Polling timeout: 180000ms

## Chat UI

Progressive chat, without LLM.
Messages prompting for user input get pushed one at a time:

**1. Select Outcome**:

- Trigger: initial assistant message
- Text: vocabulary.messages.selectOutcome
- Available outcomes as suggestions

**2. Upload Reference Image**:

- Trigger: user selected an outcome
- Text: vocabulary.messages.uploadReference
- File upload + uploaded photo appears inline

**3. Request Inference**:

- Trigger: user uploaded reference
- Text: vocabulary.messages.requestInference
- Submit button inline, enabled if reference + outcome valid

**4. Inference Busy**:

- Trigger: user initated inference
- Text: no text for 35s, vocabulary.messages.busyForAWhile after
- Assistant loading message

**5.a Inference Rejected**:

- Trigger: inference failed
- Text: vocabulary.messages.rejected

**5.b Inference Fulfilled**:

- Trigger: inference fulfilled, image received
- Text: vocabulary.messages.fulfilled
- Received image appears inline
