# DEPS_PLAN: Nx Dependency Chain for GPU Workers → Router → Consumer

## Objective
Wire Nx so `gpu-workers-flux2` / `gpu-workers-tiny-sd` deploy targets emit `dist/.../contract.json`, `worker-router:build-manifest` reads them to generate both a provider manifest + auth token, and `worker-router:deploy` pushes the token to Cloudflare secrets before deploying both instances. Consumer (face-value) reads the token from the same `dist/` file at build time.

---

## Gap 1: Replace Beam deploy stub with real output emitter

**Files:** `apps/gpu-workers/flux2/project.json` (lines 43-48), `apps/gpu-workers/tiny_sd/project.json` (same), NEW `scripts/deploy-beam.mjs`

Replace the echo stub:
```jsonc
"deploy-beam": {
  "executor": "nx:run-commands",
  "options": { "command": "node scripts/deploy-beam.mjs", "cwd": "." },
  "dependsOn": ["verify-deploy-gate"],
  "cache": false,
  "outputs": ["dist/apps/gpu-workers-flux2"]  // NEW
}
```

`apps/gpu-workers/flux2/scripts/deploy-beam.mjs` (NEW):
```javascript
import { readFileSync, mkdirSync, writeFileSync } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"
const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..")
const yaml = readFileSync(join(root, "apps/gpu-workers/flux2/beam.yaml"), "utf-8")
const match = yaml.match(/^project:\s*(.+)$/m)
if (!match) throw new Error("no project in beam.yaml")
const project = match[1].trim()
const out = join(root, "dist", "apps", "gpu-workers-flux2")
mkdirSync(out, { recursive: true })
writeFileSync(join(out, "contract.json"), JSON.stringify({
  url: `https://${project}.app.beam.cloud`,
  taskApi: "https://api.beam.cloud"
}, null, 2))
console.log(`wrote dist/apps/gpu-workers-flux2/contract.json`)
```

Same pattern for tiny_sd (reads `tiny_sd/beam.yaml` or derives from project name).

---

## Gap 2: Replace Flash deploy stub with real output emitter

**Files:** `apps/gpu-workers/flux2/project.json` (lines 49-54), `scripts/deploy-flash.py` (NEW), `scripts/flash-output.mjs` (NEW)

```jsonc
"deploy-flash": {
  "executor": "nx:run-commands",
  "options": {
    "command": "uv run --locked python scripts/deploy-flash.py && node scripts/flash-output.mjs",
    "cwd": "."
  },
  "dependsOn": ["verify-deploy-gate"],
  "cache": false,
  "outputs": ["dist/apps/gpu-workers-flux2"]  // NEW
}
```

`apps/gpu-workers/flux2/scripts/deploy-flash.py` (NEW):
```python
import subprocess, sys, re, os
result = subprocess.run(["flash", "deploy", "--name", "flux2"], capture_output=True, text=True)
if result.returncode != 0:
    print(result.stderr, file=sys.stderr)
    sys.exit(1)
match = re.search(r'endpoint[_\s-]?id[:\s]+(\w+)', result.stderr, re.IGNORECASE)
endpoint_id = match.group(1) if match else "flux2"
with open(".flash_endpoint_id", "w") as f:
    f.write(endpoint_id)
```

`apps/gpu-workers/flux2/scripts/flash-output.mjs` (NEW):
```javascript
import { readFileSync, mkdirSync, writeFileSync } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"
const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..")
const endpointId = readFileSync(join(root, "apps/gpu-workers/flux2/.flash_endpoint_id"), "utf-8").trim()
const out = join(root, "dist", "apps", "gpu-workers-flux2")
mkdirSync(out, { recursive: true })
writeFileSync(join(out, "contract.json"), JSON.stringify({
  url: `https://endpoints.runpod.io/v2/${endpointId}`,
  endpointId
}, null, 2))
console.log(`wrote dist/apps/gpu-workers-flux2/contract.json`)
```

---

## Gap 3: Modal deploy emits output instead of router deriving from source

**Files:** `apps/gpu-workers/flux2/project.json` (lines 37-42), `scripts/modal-output.mjs` (NEW)

```jsonc
"deploy-modal": {
  "executor": "nx:run-commands",
  "options": {
    "command": "uv run --locked modal deploy flux2/worker_modal_cls_flux2_klein9b.py && node scripts/modal-output.mjs",
    "cwd": "."
  },
  "dependsOn": ["verify-deploy-gate"],
  "cache": false,
  "outputs": ["dist/apps/gpu-workers-flux2"]  // NEW
}
```

`apps/gpu-workers/flux2/scripts/modal-output.mjs` (NEW):
```javascript
import { readFileSync, mkdirSync, writeFileSync } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"
const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..")
const py = readFileSync(join(root, "apps/gpu-workers/flux2/worker_modal_cls_flux2_klein9b.py"), "utf-8")
const appMatch = py.match(/modal\.App\("([^"]+)"\)/)
const clsMatch = py.match(/class\s+(\w+).*(?=generate)/s)
if (!appMatch) throw new Error("no modal.App in worker")
const app = appMatch[1]
const cls = clsMatch ? clsMatch[1] : "FluxKleinWorker"
const out = join(root, "dist", "apps", "gpu-workers-flux2")
mkdirSync(out, { recursive: true })
writeFileSync(join(out, "contract.json"), JSON.stringify({
  url: `https://${app}--queue-api.modal.run`,
  app, cls
}, null, 2))
console.log(`wrote dist/apps/gpu-workers-flux2/contract.json`)
```

---

## Gap 4: Rewrite build-manifest.mjs to read from dist/ contract files

**File:** `apps/worker-router/scripts/build-manifest.mjs` — COMPLETE REWRITE

Reads `dist/apps/gpu-workers-flux2/contract.json` + `dist/apps/gpu-workers-tiny-sd/contract.json` → writes:
1. `src/lib/providers.generated.json` — consumed by router source (ProviderCoordinates per contract)
2. `dist/apps/worker-router/contract.json` — consumed by consumer apps (token + router URLs)

```javascript
import { readFileSync, mkdirSync, writeFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"
const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..")

const models = [
  { dir: "flux2", contract: "flux2_klein9b", modelKey: "gpu-workers-flux2" },
  { dir: "tiny_sd", contract: "tiny_sd", modelKey: "gpu-workers-tiny-sd" }
]

function loadContract(modelKey) {
  try {
    const path = join(root, "dist", "apps", modelKey, "contract.json")
    return JSON.parse(readFileSync(path, "utf-8"))
  } catch { return null }
}

const providerManifest = {}
for (const model of models) {
  const c = loadContract(model.modelKey)
  providerManifest[model.contract] = {
    beam: c?.url ? { invokeUrl: c.url, taskApi: c.taskApi || "https://api.beam.cloud" } : null,
    flash: c?.url ? { baseUrl: c.url } : null,
    modal: c?.url ? { baseUrl: c.url } : null
  }
}

const token = process.env.ROUTER_SECRET || `router-${new Date().toISOString().slice(0,10)}-${Math.random().toString(36).slice(2,8)}`
const out = join(root, "dist", "apps", "worker-router")
mkdirSync(out, { recursive: true })

const distContract = {
  authToken: token,
  endpoints: {
    flux2: "https://worker-router-flux2.gyorgy-gutai.workers.dev",
    tiny_sd: "https://worker-router-tinysd.gyorgy-gutai.workers.dev"
  },
  providers: providerManifest
}
writeFileSync(join(out, "contract.json"), JSON.stringify(distContract, null, 2))

const srcOut = join(root, "apps", "worker-router", "src", "lib", "providers.generated.json")
mkdirSync(dirname(srcOut), { recursive: true })
writeFileSync(srcOut, JSON.stringify(providerManifest, null, 2) + "\n")
console.log(`wrote dist/apps/worker-router/contract.json + src/lib/providers.generated.json`)
```

---

## Gap 5: Router deploy target pushes token to Cloudflare

**Files:** `apps/worker-router/project.json` (deploy target), `scripts/deploy.mjs` (NEW)

`apps/worker-router/scripts/deploy.mjs` (NEW):
```javascript
import { readFileSync } from "node:fs"
import { execSync } from "node:child_process"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"
const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..")
const contract = JSON.parse(readFileSync(join(root, "dist", "apps", "worker-router", "contract.json"), "utf-8"))
execSync(`echo "${contract.authToken}" | npx wrangler secret put AUTH_TOKEN`, { stdio: "inherit", cwd: process.cwd() })
execSync("npx wrangler deploy --env flux2", { stdio: "inherit", cwd: process.cwd() })
execSync("npx wrangler deploy --env tinysd", { stdio: "inherit", cwd: process.cwd() })
```

```jsonc
"deploy": {
  "executor": "nx:run-commands",
  "options": { "command": "node scripts/deploy.mjs", "cwd": "apps/worker-router" },
  "dependsOn": [
    "build-manifest",
    "gpu-workers-flux2:deploy-modal", "gpu-workers-flux2:deploy-beam", "gpu-workers-flux2:deploy-flash",
    "gpu-workers-tiny-sd:deploy-modal", "gpu-workers-tiny-sd:deploy-beam", "gpu-workers-tiny-sd:deploy-flash"
  ],
  "cache": false
}
```

---

## Gap 6: Consumer wiring (face-value)

**File:** `apps/face-value/project.json`

```jsonc
"implicitDependencies": ["worker-router"],
"targets": {
  "build": {
    "dependsOn": [{ "projects": ["worker-router"], "target": "build-manifest" }]
  },
  "dev": {
    "dependsOn": [{ "projects": ["worker-router"], "target": "build-manifest" }]
  }
}
```

**File:** `apps/face-value/src/lib/router-config.ts` (NEW — server-side only)

```typescript
// Server-only import — never client-side (Next.js process.cwd() points to dist/)
const contract = require("../../../dist/apps/worker-router/contract.json")

export const routerConfig = {
  token: contract.authToken,
  endpoints: {
    flux2: contract.endpoints.flux2,
    tiny_sd: contract.endpoints.tiny_sd
  }
}
```

Consumer route handler uses `routerConfig` server-side only:
```typescript
// apps/face-value/src/app/api/infer/route.ts
import { routerConfig } from "@/lib/router-config"
export async function POST(req) {
  const body = await req.json()
  const res = await fetch(routerConfig.endpoints.flux2, {
    method: "POST",
    headers: { "Authorization": `Bearer ${routerConfig.token}`, "content-type": "application/json" },
    body: JSON.stringify(body)
  })
  return new Response(res.body, { status: res.status })
}
```

---

## Gap 7: Spec wording changes

### `apps/worker-router/AGENTS.md` — Authentication section:
```diff
 **Authentication**:
- - Bearear auth header guarding all endpoints
- - Auth token generated at deploy (build) time
- - Consumer apps receive auth token at build time to use at runtime
+ - Bearer auth header guarding all endpoints
+ - Auth token generated at build-manifest time, written to `dist/apps/worker-router/contract.json`
+ - Token is pushed to Cloudflare via `wrangler secret put` during `worker-router:deploy`
+ - Consumer apps read token from `dist/apps/worker-router/contract.json` at their build time
```

### `apps/worker-router/AGENTS.md` — Dependencies section:
```diff
 **Each deployment depends on**:
- - an input/output contract e.g. "flux2" - generates TS on deploy
- - the deployed worker implementations of that contract (for usls)
- - reusable, one deployment of router per contract type, configured
+ - deployed worker contract outputs: `dist/apps/gpu-workers-flux2/contract.json`, `dist/apps/gpu-workers-tiny-sd/contract.json`
+ - generated provider manifest: `src/lib/providers.generated.json` (from `build-manifest` target reading dist/ contracts)
+ - consumer receives auth token from `dist/apps/worker-router/contract.json` at build time
```

### `apps/worker-router/AGENTS.md` — Example Use Case:
```diff
 **Example Use Case**
-- Router deployed with build time deps:
-  - Using packages/contracts/src/small_vision.json
-  - Deployed provider worker urls
-- Any consumers depending on that router configuration
-  - Redeployed, receiving contracts and generated token at build time
+- `nx run worker-router:deploy` triggers the full Nx chain:
+  1. `gpu-workers-flux2:deploy-*` writes `dist/apps/gpu-workers-flux2/contract.json`
+  2. `gpu-workers-tiny-sd:deploy-*` writes `dist/apps/gpu-workers-tiny-sd/contract.json`
+  3. `worker-router:build-manifest` reads dist/ contracts → writes `dist/apps/worker-router/contract.json` (token + endpoints)
+  4. `worker-router:deploy` pushes token to Cloudflare secrets, deploys both `--env flux2` and `--env tinysd`
+  5. Consumer `build` reads `dist/apps/worker-router/contract.json` for token + router URLs
 - Runtime:
   - Consumer can send tasks to router, sending token and input
   - Router receives request at /queue, pick provider, sends task to provider queue
   - Upon success, responds with task id using the unified contract
   - Client can poll router /task to get status and any output (non-null output means done)
```

### `apps/gpu-workers/AGENTS.md` — After each provider section:
> **Nx integration**: `deploy-{platform}` target writes `dist/apps/gpu-workers-{model}/contract.json` with provider-specific deployment metadata (URL, IDs). This file is consumed by `worker-router:build-manifest`.

---

## Execution Order

1. Create `deploy-beam.mjs` for flux2 + tiny_sd
2. Create `deploy-flash.py` + `flash-output.mjs` for flux2 + tiny_sd
3. Create `modal-output.mjs` for flux2 + tiny_sd
4. Update `gpu-workers/flux2` and `gpu-workers/tiny_sd` `project.json` (add `outputs` to deploy-modal|deploy-beam|deploy-flash)
5. Rewrite `worker-router/scripts/build-manifest.mjs` to read from dist/ contracts
6. Create `worker-router/scripts/deploy.mjs`
7. Update `worker-router/project.json` (deploy target → deploy.mjs, add outputs to build-manifest)
8. Wire consumer (`face-value` or `chat-ui`): implicitDependencies + dependsOn
9. Create consumer `router-config.ts`
10. Update specs: `worker-router/AGENTS.md`, `gpu-workers/AGENTS.md`
11. Run `typecheck` + `test-unit` + `lint` green on worker-router
12. Run dry-run deploy to validate full chain

---

## Notes / Trade-offs

- **Beam URL** is static from `beam.yaml` — the project name suffices for the invocation URL pattern. If Beam creates a real deploy-time URL, we'd adjust.
- **Flash endpoint ID capture** is fragile — the regex may not match all `flash deploy` output variants. Validate against a real deploy or use deploy name as fallback.
- **Token rotation** happens automatically on every `worker-router:deploy` — new token overwrites old one in `dist/` and `wrangler secret`.
- **Consumer choice** is `face-value` per the example, but `chat-ui` is the documented flux2 consumer. Picking one; can wire both later.
- **`dist/` handoff is Nx-native** — `dependsOn` ordering + `outputs` declared on each target means `nx affected -t build` chains correctly. No custom orchestration.
