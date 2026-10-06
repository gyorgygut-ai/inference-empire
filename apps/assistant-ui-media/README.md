# with-image-generation

Minimal Next.js example that generates an image through a server route and renders it with the `@assistant-ui/ui` `Image` component (loading, content-filter, zoom, and download / copy / regenerate actions). It runs with credentials; `FLUX2_ROUTER_URL` and `FLUX2_ROUTER_TOKEN` must be configured.

## Run locally

```bash
export FLUX2_ROUTER_URL=https://flux2-router-worker.gyorgy-gutai.workers.dev
export FLUX2_ROUTER_TOKEN=...
npx nx dev assistant-ui-media
```

Then open `http://localhost:3000`.

## How it works

- `app/api/image/route.ts` exposes a server endpoint that submits the prompt to the Flux2 router worker (`POST /queue` with `{ input }`, then polls `GET /task/:id` until `DONE`) and returns an `ImageMessagePart`-shaped payload. With `FLUX2_ROUTER_URL` and `FLUX2_ROUTER_TOKEN` configured it returns the generated image; if not configured it responds with a 503 error.
- `app/page.tsx` POSTs the prompt to that endpoint, stores the result as an `ImageMessagePart`, and renders it with the `@assistant-ui/ui` `Image` component.
- `Image.Actions` provides download and copy buttons plus a regenerate button wired through its `onRegenerate` callback.
