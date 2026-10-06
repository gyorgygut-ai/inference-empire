# SPECS

**Project goal**: a NextJS app demonstrating a selection of NextJS features - most introduced in the last 1.5 years.

## Shared Vocabulary

- **Reference image** — the face photo submitted by the user for transformation
- **Image gen prompt** — the text instruction sent to the inference server, sourced from an outcome `.md` file, never exposed to client
- **Inference backend** — `worker-router-flux2` Cloudflare Worker (`flux2_klein9b` contract), receives reference image + prompt, returns generated image
- **Inference server** — (legacy) RunPod endpoint; deprecated, kept in `schema.ts` for contract parity
- **Outcome** — a `.md` file in `/outcomes` defining an image gen prompt, identified by id; also the transformation effect the user selects
- **Generated image** — the image returned by the inference server after processing reference image + prompt

## Core Features

- Upload a reference image
- Select an outcome
- Submit posts to `worker-router-flux2` `/queue`, polls `/task/:id` until DONE, returns generated image
- Generated image displayed inline, downloadable

## Key Decisions

### NextJS non-negotiables

- **Server Components**: static shell, outcome prompts server-only. [Server and Client Components](https://nextjs.org/docs/app/getting-started/server-and-client-components)
- **Server Actions**: reference image submit + Flux call, no API routes. [Server Actions and Mutations](https://nextjs.org/docs/app/building-your-application/data-fetching/server-actions-and-mutations)
- **React Compiler**: zero manual memoization. [React Compiler](https://react.dev/learn/react-compiler)

### Business Logic

- **Magic Encapsulated**:
  - `worker-router-flux2` URL derived from `dist/apps/flux2/contract.json` (`workerUrl`, emitted by `flux2-router:deploy`) at build time via server-only `router-config.ts`, never exposed to client
  - Auth token never written to disk: Cloudflare secret on the worker side, `FLUX2_ROUTER_TOKEN` build env on the face-value side
  - Client sends reference image + selected outcome id upon submit to Server Action
  - Server Action posts outcome prompt + reference image to `worker-router-flux2` `/queue`, polls `/task/:id` until DONE or timeout (max 5 min, poll interval 3s)
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
  - Sent as base64
  - Server validates type, size, format before sending to inference server

### Styling and Layout

- Tailwind v4 + assistant-ui registry components (see assistant-ui section)

### Inference Backend

- **Worker router (flux2)** — `POST /queue` with `{ input: Flux2Klein9BInput }` + `Authorization: Bearer <token>` → `{ task_id }` (202), then `GET /task/:task_id` with auth → `{ status: "BUSY"|"REJECTED"|"DONE", output?: Flux2Klein9BOutput }`. Poll every 3s, max 50s (Vercel Hobby function cap).
- **Provider routing** — flux2 worker-router internally routes to Modal/Flash/Beam providers from private `dist/apps/flux2/provider.json` (merged `{modal, beam, flash}` entries, beam bundled dormant). face-value never calls providers directly and never sees provider URLs.
- **Auth token** generated at deploy time, set as Cloudflare secret on the worker, passed to face-value builds via `FLUX2_ROUTER_TOKEN` env. Ephemeral copy in gitignored `dist/*/.router-token` as Nx handoff between router deploy and client env injection; never committed, never shipped to Vercel.
- **Vercel (Hobby)** — Root Directory `apps/face-value`. Worker URL via `FLUX2_ROUTER_URL` env (`router-config.ts` uses it first, `dist` contract file only as local fallback). Inference budget 50s (`timeoutMs: 50 * 1000`, 3s poll) under the 60s function cap; slow GPU runs surface as timeout errors. Node pinned via `engines: 22.x`.
- **Model**: `flux_2_klein_9b_q6p.ckpt` (~7.3GB) — hosted on `flux2/` provider backend. Deployment managed separately via Nx chain.

### Security

- Cloudflare Access JWT gate in `proxy.ts` against CF certs, redirect on invalid token; no-op without CF env vars. Origin stays private behind CF.

### Error States

- Reference image missing → send blocked by pre-send validation, no submission
- Reference image exceeds size limit → client-side error before submission
- Worker-router unreachable (401/404/502) → error text in assistant message
- Worker-router returns REJECTED → error text in assistant message
- Timeout after 50s polling → SERVER_TIMEOUT error text

### API Contract - Worker Router (flux2)

- `POST /queue` — `Authorization: Bearer <token>`, `Content-Type: application/json`, body: `{ input: Flux2Klein9BInput }` → 202 `{ task_id: string }`
- `GET /task/:task_id` — `Authorization: Bearer <token>` → 200 `{ status: "BUSY"|"REJECTED"|"DONE", output?: Flux2Klein9BOutput }`
- Error responses: 400 `{ error: "Bad request" }`, 401 `{ error: "Unauthorized" }`, 404 `{ error: "Not found" }`, 500 `{ error: "Internal server error" }`
- Contract name bound to Cloudflare Worker env var: `flux2_klein9b`

### Legacy API Contract — RunPod (deprecated)

[API Typescript schema](../app/inference-api/schema.ts) — types retained for contract parity. No longer used at runtime.

**Layout**:

- full-width chat by default.
- > `lg`: 2-column: left 2/3 (solid bg, hero img), right 1/3 (chat)

## assistant-ui thread

**Non-negotiables**:

- Progressive chat stream. No LLM. No chat message input.
- `useLocalRuntime` bridges to existing Server Action
- Each step is just a new message in the thread
- Each message encapsulated in a `Message**` component
- Multi-turn: previous outcome and ref. image can be changed in the original message
- BE contract canonical in `dist/apps/flux2/contract.json` (`{workerName, workerUrl, contractName, input, output}`, emitted by `flux2-router:deploy`), read at build time via server-only `router-config.ts`. `schema.ts` is generated from that file's `.input`/`.output` only. Requests go through `@inference/worker-router-client: inferWithPolling`.
- assistant-ui registry components (`thread` + `image`, plus `attachment`, `file`, `tooltip-icon-button`, shadcn ui set); LLM-only elements trimmed

**Critical**:

- This is NOT a wizard - old messages still rendered after new appended
- Each new message gets pushed into the thread as task in previous msg completes

**1. message: `MessageOutcomeSelect`**:

- Message: vocabulary.messages.selectOutcome
- Outcomes rendered from server `{id, title}`, `SuggestionPrimitive`

**message: `MessageUploadReference`**:

- Message: vocabulary.messages.uploadReference
- Image upload via `AttachmentPrimitive` in message
- Selected image displayed in chat, removable

**message: `MessageRequestInference`**:

- Button: vocabulary.messages.requestInference
- Can become disabled as previous selections change

**message: `MessageArtifact`**:

- **state: busy**:
  - Message: vocabulary.messages.busy
  - Message after 35 seconds: vocabulary.messages.busyForAWhile
  - Content: placeholder image

- **state: rejected**:
  - Message: vocabulary.messages.rejected

- **state: fulfilled**:
  - Message: vocabulary.messages.fulfilled
  - Content: generated image
