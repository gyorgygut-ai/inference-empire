# Per-target Criteria

## 🧭 router:dev-flux2

**Acceptance Criteria**:

- [ ] `{workspaceRoot}/dist/flux2/dev.env`: `MODAL_WORKER_URL` exists
- [ ] `{workspaceRoot}/dist/flux2/dev.env`: `BEAM_WORKER_URL` exists
- [ ] `{workspaceRoot}/dist/flux2/dev.env`: `ROUTER_URL` is `http://127.0.0.1:5040`
- [ ] `{workspaceRoot}/dist/flux2/dev.env`: `ROUTER_AUTH_TOKEN` exists
- [ ] `@packages/contracts/generated/flux2_api.ts` exists
- [ ] POST `http://127.0.0.1:5040/q` (no token) → 401
- [ ] GET `http://127.0.0.1:5040/sup` (no token) → 401
- [ ] POST `http://127.0.0.1:5040/q` + `Authorization: Bearer ${ROUTER_AUTH_TOKEN}` + valid body → `{ task_id: ${task_id} }`
- [ ] GET `http://127.0.0.1:5040/sup?id=${task_id}` + `Authorization: Bearer ${ROUTER_AUTH_TOKEN}` → `{ status: ... }`

## 🧭 router:dev-krea2

**Acceptance Criteria**:

- [ ] `{workspaceRoot}/dist/krea2/dev.env`: `MODAL_WORKER_URL` exists
- [ ] `{workspaceRoot}/dist/krea2/dev.env`: `ROUTER_URL` is `http://127.0.0.1:5042`
- [ ] `{workspaceRoot}/dist/krea2/dev.env`: `ROUTER_AUTH_TOKEN` exists
- [ ] `@packages/contracts/generated/krea2_api.ts` exists
- [ ] POST `http://127.0.0.1:5042/q` (no token) → 401
- [ ] GET `http://127.0.0.1:5042/sup` (no token) → 401
- [ ] POST `http://127.0.0.1:5042/q` + `Authorization: Bearer ${ROUTER_AUTH_TOKEN}` + valid body → `{ task_id: ${task_id} }`
- [ ] GET `http://127.0.0.1:5042/sup?id=${task_id}` + `Authorization: Bearer ${ROUTER_AUTH_TOKEN}` → `{ status: ... }`

## 🧭 router:dev-flux2 + router:dev-krea2 (parallel)

**Acceptance Criteria**:

- [ ] Both listen simultaneously: `http://127.0.0.1:5040` and `http://127.0.0.1:5042`
- [ ] No port clash
- [ ] `dist/flux2/dev.env` and `dist/krea2/dev.env` written independently; no cross-write

## 💬 face-value:dev

**Acceptance Criteria**:

- [ ] `{workspaceRoot}/dist/flux2/dev.env`: `MODAL_WORKER_URL` exists
- [ ] `{workspaceRoot}/dist/flux2/dev.env`: `BEAM_WORKER_URL` exists
- [ ] `{workspaceRoot}/dist/flux2/dev.env`: `ROUTER_URL` is `http://127.0.0.1:5040`
- [ ] `{workspaceRoot}/dist/flux2/dev.env`: `ROUTER_AUTH_TOKEN` exists
- [ ] `@packages/contracts/generated/flux2_api.ts` exists
- [ ] GET `http://127.0.0.1:3000` → 200
- [ ] `ROUTER_AUTH_TOKEN` not reachable from the browser bundle

## 💬 face-value:deploy

**Acceptance Criteria**:

- [ ] `{workspaceRoot}/dist/flux2/deploy.env`: `MODAL_WORKER_URL` exists
- [ ] `{workspaceRoot}/dist/flux2/deploy.env`: `BEAM_WORKER_URL` exists
- [ ] `{workspaceRoot}/dist/flux2/deploy.env`: `ROUTER_URL` exists (deployed URL)
- [ ] `{workspaceRoot}/dist/flux2/deploy.env`: `ROUTER_AUTH_TOKEN` exists
- [ ] `@packages/contracts/generated/flux2_api.ts` exists
- [ ] POST `${ROUTER_URL}/q` (no token) → 401
- [ ] POST `${ROUTER_URL}/q` + `Authorization: Bearer ${ROUTER_AUTH_TOKEN}` + valid body → `{ task_id: ${task_id} }` (returning `task_id` implies the deployed router reached the worker, i.e. its `MODAL/BEAM_WORKER_URL` runtime env is set)
- [ ] GET `${ROUTER_URL}/sup?id=${task_id}` + `Authorization: Bearer ${ROUTER_AUTH_TOKEN}` → `{ status: ... }`
- [ ] GET `${FACE_VALUE_URL}` → 200
