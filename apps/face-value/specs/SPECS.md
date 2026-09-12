# SPECS

**Project goal**: a NextJS app demonstrating a selection of NextJS features - most introduced in the last 1.5 years.

## Shared Vocabulary

- **Reference image** — the face photo submitted by the user for transformation
- **Image gen prompt** — the text instruction sent to the inference server, sourced from an outcome `.md` file, never exposed to client
- **Inference server** — tThings gRPC server running in Docker on RunPod, receives reference image + prompt, returns generated image
- **Outcome** — a `.md` file in `/outcomes` defining an image gen prompt, identified by id; also the transformation effect the user selects
- **Generated image** — the image returned by the inference server after processing reference image + prompt

## Core Features

- Upload a reference image
- Select an outcome
- Submit generates an image on cloud GPU (Runpod)
- Generated image displayed inline, downloadable
- Access gated behind Cloudflare Access email OTP

## Key Decisions

### NextJS non-negotiables

- **Server Components**: static shell, outcome prompts server-only. [Server and Client Components](https://nextjs.org/docs/app/getting-started/server-and-client-components)
- **Server Actions**: reference image submit + Flux call, no API routes. [Server Actions and Mutations](https://nextjs.org/docs/app/building-your-application/data-fetching/server-actions-and-mutations)
- **useActionState**: form state, errors, pending. [useActionState](https://react.dev/reference/react/useActionState)
- **useFormStatus**: disable submit while generating. [useFormStatus](https://react.dev/reference/react-dom/hooks/useFormStatus)
- **useOptimistic**: instant placeholder, swap on result. [useOptimistic](https://react.dev/reference/react/useOptimistic)
- **proxy.ts**: CF JWT verification, blocks origin bypass. [Next.js 16 Blog](https://nextjs.org/blog/next-16)
- **fetch cache**: same reference image + outcome cached forever, abuse prevention. [Caching](https://nextjs.org/docs/app/building-your-application/caching)
- **React Compiler**: zero manual memoization. [React Compiler](https://react.dev/learn/react-compiler)
- **Async cookies**: await cookies() for CF auth header. [Sync Dynamic APIs](https://nextjs.org/docs/messages/sync-dynamic-apis)

### Business Logic

- **Magic Encapsulated**:
  - Inference server url, image gen. mode, prompts hidden from client
  - Client sends reference image + selected outcome id upon submit to Server Action
  - Server Action sends corresponding outcome prompt + reference image to inference server
  - Upon response, serves generated image or error message to client
- **Markdown + Frontmatter**:
  - Each outcome is a .md file in /outcomes
  - Frontmatter: (id, title, width, height, prompt)
  - Never exposed to client as is, id and title for display only
- ~~**No CSS Styles, Almost**:~~ POSTPONED for assistant-ui chat
  - ~~Sloppy styling for that authentic early-2000s aesthetic~~
  - ~~Some control of appearance can, and should be achieved via semantic elements~~
- **Proper Data Handling**:
  - Where data is dynamic, the "empty, 1, many data" cases should be handled
  - Same goes for loading, success, error states at the minimum
- **Reference Image Handling**:
  - User uploads their own image
  - Resized to max 512×512 on server before sending to inference server
  - Sent as base64

### Styling and Layout

- Zero CSS, native semantic HTML elements only
- Hero `<img>` intrinsic width controls layout
- `❌` emoji for error
- `<button disabled>` + text swap for loading

### Image Generation Form

- `useActionState` — JS-enhanced, degrades to full POST
- `<select>` in form
- Native: `accept`, `required`
- Server: type, size, format validation
- File → base64 → BE
- Request-time rendered page + server action; health ping at render (1000ms, fail-open) — submit enabled by default, disabled + `❌ Server offline` when ping fails
- Result `<img />`
- `<a download>` for download

### Inference Backend

- On-demand inference server in Docker on RunPod serverless
- Model: `flux_2_klein_9b_q6p.ckpt` (~7.3GB)

### Auth

- ~~Cloudflare Access email OTP in front of the domain~~
- ~~CF JWT verified in `proxy.ts` via `jose` against CF public certs~~
- ~~Origin URL kept private — CF is the only entry point~~

### Security

- TODO: oh the irony

### Caching

- Same reference image + outcome combo: `fetch` cache with `revalidate: false`
- Cache key: reference image hash + outcome id

### Abuse Prevention

- Fetch cache eliminates duplicate inference calls
- CF Access gates the app from public access

### Error States

- Reference image missing → form error, no submission
- Reference image exceeds size limit → client-side error before submission
- Inference server unreachable → server error returned to client
- Health ping fails → submit disabled, `❌ Server offline` shown
- Inference server returns error → error message displayed in result area
- CF JWT invalid → redirect to CF Access login

### API Contract - Inference Server

[API Typescript schema](./types/schema.ts)

## assistant-ui

- Chat interface replaces form UI. No LLM involved.
- Runtime: `useLocalRuntime` bridges to existing Server Action (`requestOutcome` in `app/actions.ts`). No API routes.
- Primitives: `ThreadPrimitive`, `ComposerPrimitive`, `AttachmentPrimitive`, `SuggestionPrimitive`, `AuiIf`.
- Outcomes rendered as `SuggestionPrimitive` items in thread.
- Image upload via `AttachmentPrimitive` in composer after outcome selection.
- Generated image rendered as `ImageMessagePart` in assistant message, with download action.
- Error and loading states shown as system/running messages in thread.
- Server offline → disabled composer + system message.
- Pre-send validation: send button disabled until outcome selected + image attached.
- Multi-turn: previous image persists as visible attachment in composer across turns.
- Model fallback handled by external Cloudflare gateway proxy. This app calls gateway; no fallback logic here.
- BE contract canonical in `inference-tooling` repo (beam + modal workers). Runpod flash out of service. This repo's `schema.ts` mirrors canonical contract.
- Styling: assistant-ui registry components (`npx assistant-ui@latest add thread`, `npx assistant-ui@latest add image`). Project uses Tailwind v4.
- Layout: full-width chat by default. At `lg` breakpoint → 2-column: left 2/3 (solid bg, hero img), right 1/3 (chat). Tailwind grid on page wrapper.
