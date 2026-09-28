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
- **In-memory cache**: same reference image + outcome served without re-inference, abuse prevention. [Caching](https://nextjs.org/docs/app/building-your-application/caching)
- **React Compiler**: zero manual memoization. [React Compiler](https://react.dev/learn/react-compiler)

### Business Logic

- **Magic Encapsulated**:
  - `worker-router-flux2` URL and auth token derived from `dist/apps/worker-router/contract.json` at build time via server-only `router-config.ts`, never exposed to client
  - Client sends reference image + selected outcome id upon submit to Server Action
  - Server Action posts outcome prompt + reference image to `worker-router-flux2` `/queue`, polls `/task/:id` until DONE or timeout (max 5 min, poll interval 3s)
  - Upon response, serves generated image or error message to client
- **Markdown + Frontmatter**:
  - Each outcome is a .md file in /outcomes
  - Frontmatter: (id, title, width, height, prompt)
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

- **Worker router (flux2)** — `POST /queue` with `{ input: Flux2Klein9BInput }` + `Authorization: Bearer <token>` → `{ task_id }` (202), then `GET /task/:task_id` with auth → `{ status: "BUSY"|"REJECTED"|"DONE", output?: Flux2Klein9BOutput }`. Poll every 3s, max 5 min.
- **Provider routing** — flux2 worker-router internally routes to Modal/Flash/Beam providers based on `providers.generated.json` (written by `worker-router:build-manifest` reading `dist/apps/gpu-workers-flux2/contract.json`). face-value never calls providers directly.
- **Auth token** generated at build time, injected into `dist/apps/worker-router/contract.json`.
- **Model**: `flux_2_klein_9b_q6p.ckpt` (~7.3GB) — hosted on `gpu-workers-flux2/` provider backend. Deployment managed separately via Nx chain.

### Security

- TODO: oh the irony

### Caching

- Same reference image + outcome combo cached in-memory (`app/inference-cache.ts`), lost on restart
- Cache key: sha256(reference image) + outcome id

### Abuse Prevention

- In-memory cache eliminates duplicate inference calls

### Error States

- Reference image missing → send blocked by pre-send validation, no submission
- Reference image exceeds size limit → client-side error before submission
- Worker-router unreachable (401/404/502) → error text in assistant message
- Worker-router returns REJECTED → error text in assistant message
- Timeout after 5 min polling → SERVER_TIMEOUT error text

### API Contract - Worker Router (flux2)

- `POST /queue` — `Authorization: Bearer <token>`, `Content-Type: application/json`, body: `{ input: Flux2Klein9BInput }` → 202 `{ task_id: string }`
- `GET /task/:task_id` — `Authorization: Bearer <token>` → 200 `{ status: "BUSY"|"REJECTED"|"DONE", output?: Flux2Klein9BOutput }`
- Error responses: 400 `{ error: "Bad request" }`, 401 `{ error: "Unauthorized" }`, 404 `{ error: "Not found" }`, 500 `{ error: "Internal server error" }`
- Contract name bound to Cloudflare Worker env var: `flux2_klein9b`

### Legacy API Contract — RunPod (deprecated)

[API Typescript schema](./types/schema.ts) — types retained for contract parity. No longer used at runtime.

## assistant-ui

- Chat interface replaces form UI. No LLM involved.
- Runtime: `useLocalRuntime` bridges to existing Server Action (`requestOutcome` in `app/actions.ts`). No API routes.
- Primitives: `ThreadPrimitive`, `ComposerPrimitive`, `AttachmentPrimitive`, `SuggestionPrimitive`, `AuiIf`.
- Outcomes rendered as `SuggestionPrimitive` items in thread.
- Image upload via `AttachmentPrimitive` in composer after outcome selection.
- Generated image rendered as `ImageMessagePart` in assistant message, with download action.
- Error and loading states shown as system/running messages in thread.
- Pre-send validation: send button disabled until outcome selected + image attached.
- Multi-turn: previous image persists as visible attachment in composer across turns.
- Model fallback handled by external Cloudflare gateway proxy. This app calls gateway; no fallback logic here.
- BE contract canonical in `dist/apps/worker-router/contract.json`, read at build time via server-only `router-config.ts`. This repo's `schema.ts` mirrors the canonical contract.
- Styling: assistant-ui registry components (`thread` + `image`, plus `attachment`, `file`, `tooltip-icon-button`, shadcn ui set) vendored manually into `components/` + `hooks/`; LLM-only elements trimmed. Project uses Tailwind v4.
- Layout: full-width chat by default. At `lg` breakpoint → 2-column: left 2/3 (solid bg, hero img), right 1/3 (chat). Tailwind grid on page wrapper.
