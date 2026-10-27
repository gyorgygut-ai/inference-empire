# Verification Plan — `face-value:dev` / `face-value:deploy`

Manual, human-run acceptance of both chains: generated env artifacts → router auth → modal/beam
workers → a real image generation with an R2 presigned URL → the deployed URLs.

Acceptance criteria: `{workspaceRoot}/AGENTS.md` → _Acceptance Criteria_.

---

## Prerequisites

- [ ] `node -v` ≥ 22, `uv --version` resolves, `npx vercel --version` = 55.0.0
- [ ] Root `.env` has `HF_TOKEN`, `R2_ACCESS_KEY`, `R2_SECRET_KEY`, `R2_ENDPOINT`, `R2_BUCKET`,
      `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET`, `FLUX2_ROUTER_URL`
- [ ] **Deploy only** — `FLUX2_ROUTER_VERCEL_*` / `FACE_VALUE_VERCEL_*` filled in root `.env`, and
      these Vercel projects exist with **Root Directory** `apps/router` / `apps/face-value`,
      **Deployment Protection (Vercel Authentication) disabled** and env supplied per deployment:
      - `router-flux2` = `prj_i6BFErhC2Znjha5kHYgSwFzZhm6c`
      - `router-krea2` = `prj_JKvkpSDegXCmwbFYBcz6enzo1bK5`
      - `face-value` = `${FACE_VALUE_VERCEL_PROJECT_ID}` (gitignored environment)
- [ ] Ports 3000 and 5050 free: `lsof -iTCP:3000 -iTCP:5050 -sTCP:LISTEN` → no output

---

## Phase A — `face-value:dev`

### A1 · Prove the artifacts are produced by this run

```bash
rm -f dist/flux2/dev.env packages/schemas/flux2/schema.ts
```

### A2 · Start the chain (continuous; terminal 1)

```bash
npx nx run face-value:dev
```

Expect, in order:

- modal deploy logs a `https://….modal.run` URL
- beam serve logs a dev URL
- router prints `http://127.0.0.1:5050`
- Next prints `Local: http://localhost:3000`

### A3 · Wait for readiness (status code, not connection error)

```bash
until [ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5050)" != "000" ]; do sleep 2; done
until [ "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000)" != "000" ]; do sleep 2; done
```

### A4 · Env artifacts

- [ ] `cat dist/flux2/dev.env` contains `ROUTER_AUTH_TOKEN`, `ROUTER_URL=http://127.0.0.1:5050`,
      `MODAL_WORKER_URL`, `BEAM_WORKER_URL`
- [ ] `TOKEN=$(grep '^ROUTER_AUTH_TOKEN=' dist/flux2/dev.env | cut -d= -f2-)`; `test ${#TOKEN} -ge 32`
- [ ] both worker URLs answer (any HTTP code, never `000`):
      `curl -s -o /dev/null -w '%{http_code}\n' "$(grep '^MODAL_WORKER_URL=' dist/flux2/dev.env | cut -d= -f2-)"`
      and the same for `BEAM_WORKER_URL`
- [ ] `packages/schemas/flux2/schema.ts` exists with a fresh mtime and exports `api`

### A5 · Router auth and routing

```bash
curl -si http://127.0.0.1:5050/sup                                  # 401
curl -si -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5050/sup # 400 (missing id) → token accepted
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"input":{"prompt":"a red apple on a table"}}' http://127.0.0.1:5050/q   # {"task_id":"…"}
```

- [ ] `task_id` is base64 of `modal:<original task id>`
- [ ] poll `curl -s -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:5050/sup?id=$TASK_ID"` →
      `PENDING`/`PROCESSING` → `COMPLETED` with `output.artifact.presigned_url`
- [ ] `curl -o /tmp/out.png "<presigned_url>"` → non-empty image

### A6 · face-value over HTTP

- [ ] `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000` → `200`
- [ ] no secret reaches the browser: `curl -s http://127.0.0.1:3000 | grep -c ROUTER_AUTH_TOKEN` → `0`
      and `grep -rl ROUTER_AUTH_TOKEN apps/face-value/.next/static` → no files

### A7 · Full UI E2E (browser)

1. [ ] open `http://127.0.0.1:3000` → hero image + chat
2. [ ] initial assistant message offers outcomes in a 2-column grid, sorted by `order`
       (`apps/face-value/outcomes/*.md`)
3. [ ] select an outcome → image dropzone appears
4. [ ] upload a JPEG/PNG ≤ 5 MB → approval card with the approve button
5. [ ] approve → spinner → generated image renders from the presigned URL and differs from the
       reference image

### A8 · Negative checks

- [ ] with the chain stopped, approving in the UI renders an error (no hang)
- [ ] `/sup` with a wrong token → `401`

### A9 · Teardown

- [ ] Ctrl-C terminal 1
- [ ] `lsof -iTCP:3000 -iTCP:5050 -sTCP:LISTEN` → empty
- [ ] `pgrep -fl 'tsx watch|next dev'` → empty

---

## Phase B — `face-value:deploy`

### B1 · Prove the artifacts are produced by this run

```bash
rm -f dist/flux2/deploy.env
```

### B2 · Router deploy

```bash
npx nx run router:deploy-flux2
```

- [ ] stdout is the deployed URL `https://<router-project>.vercel.app`
- [ ] `cat dist/flux2/deploy.env` → `ROUTER_URL=<that url>`, `ROUTER_AUTH_TOKEN` (≥32 chars),
      `MODAL_WORKER_URL`, `BEAM_WORKER_URL`

### B3 · Deployed router behaviour

Repeat A5 against `$ROUTER_URL` (401 → 400 → `200 task_id` → `COMPLETED` + presigned URL).
This proves `deploy-vercel.ts` forwarded `ROUTER_AUTH_TOKEN` / `MODAL_WORKER_URL` to the deployment.

### B4 · face-value deploy

```bash
npx nx run face-value:deploy
```

- [ ] stdout is `https://<face-value-project>.vercel.app`
- [ ] `dist/flux2/deploy.env` gains `FACE_VALUE_URL`; `ROUTER_URL` is unchanged from B2

### B5 · Deployed face-value

- [ ] `curl -s -o /dev/null -w '%{http_code}' $FACE_VALUE_URL` → `200`
- [ ] repeat A7 against `$FACE_VALUE_URL` — this is the authoritative proof that `ROUTER_URL` and
      `ROUTER_AUTH_TOKEN` reached the deployment (runtime `-e` variables do not appear in
      `vercel env ls`)
- [ ] on failure, `npx vercel inspect $FACE_VALUE_URL` for build logs

---

## Expected durations and failure signatures

| Observation | Cause |
| --- | --- |
| modal deploy + cold start 30–120 s | expected |
| Vercel production build 2–5 min | expected |
| UI generation poll up to 180 s | `timeoutMs` in `apps/face-value/app/actions/generate-image.ts` |
| `503 modal worker not configured` | `MODAL_WORKER_URL` absent from the router's env file |
| `usage: deploy-vercel.ts <app-dir>` | deploy command lost its `<app-dir>` positional |
| `401` in A5 / B3 | token in the env file differs from the one the router process loaded: re-run the chain and re-read the file after the router prints its URL |

---

## Phase B blocker — the deployed router function has never worked

Three pre-existing defects, all in `apps/router`, surface only after the Vercel build succeeds:

1. `src/router.ts` imports `@schema`, which Node rejects
   (`ERR_INVALID_MODULE_SPECIFIER: Invalid module "@schema" is not a valid package name`).
   `tsconfig` `paths` are type-only; `tsc` does not rewrite the specifier, and `@vercel/node`
   externalises it. Dev works because `tsx` resolves `paths`.
2. `env.schema.ts` requires `PORT` and `ROUTER_URL`; neither exists inside a deployed function
   (Vercel has no `PORT`, and `ROUTER_URL` is the *output* of the deploy) → 500.
3. No rewrite maps `/q` and `/sup` onto `api/[[...route]].ts`, which Vercel mounts at `/api/*` →
   404 at the root paths the spec and the client use.

`apps/router/vercel.json` has never contained rewrites (`git log` shows only buildCommand →
outputDirectory), so B3/B5 cannot pass until the router's deploy entry is fixed.

---

## Findings recorded, not addressed here

- `router:deploy-krea2` missing `<app-dir>` positional: **fixed** (`krea2 from-root`).
- `router:deploy-krea2` cannot select a model: `deploy-vercel.ts` accepts `--model`, but no target
  passes it and neither Vercel project sets `ROUTER_MODEL`, so both routers build the flux2 schema.
- `apps/router/AGENTS.md` `router:deploy-flux2` deps omit
  `{ target: "worker-flux2:deploy-beam", options: "forward" }`, which `apps/router/project.json`
  forwards — that is why `BEAM_WORKER_URL` lands in `deploy.env`.
- `apps/face-value/env.deploy-schema.ts` has no importer.
- Root `AGENTS.md` dev/deploy criteria reference `router:generate-auth-token`; the workspace defines
  `generate-{flux2,krea2}-auth-token-{dev,deploy}`.
- `apps/face-value/AGENTS.md` dependency `dev-flux2-generate-*` is a same-project glob that matches
  nothing in `face-value`; `apps/face-value/project.json` correctly names
  `router:dev-flux2-generate-router-url`.
- `tests/acceptance/*.e2e.ts` is not picked up by any vitest project, asserts port `5040` while
  `.env` sets `5050`, and waits for `listening on`, which `apps/router/src/serve.ts` never prints.
