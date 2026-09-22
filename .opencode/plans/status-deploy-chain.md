# Status App — Deploy Chain Integration

## Goal
Integrate `status` app into the Nx deploy chain so it deploys last, dynamically discovering monitor URLs from deployed gpu-workers and infrastructure apps.

## Architecture

```
gpu-workers:deploy-flash|deploy-beam|deploy-modal (ALL 3 for flux2 & tiny_sd)
  → writes dist/apps/gpu-workers-{model}/contract.json with deploy URL
worker-router:deploy (reads contract.json → builds manifest → deploys to *.workers.dev)
  → deployed at predictable domains (worker-router-flux2.gyorgy-gutai.workers.dev, etc.)
status:deploy (GENERATES uptime.config.ts from contracts + known URLs → builds → deploys)
  → deployed to Cloudflare Pages at status.pages.dev
```

## Files to Create/Modify

### 1. `apps/status/project.json` — Nx project definition

```json
{
  "$schema": "../../../node_modules/nx/schemas/project-schema.json",
  "name": "status",
  "projectType": "application",
  "sourceRoot": "apps/status/src",
  "tags": ["type:app", "scope:client"],
  "implicitDependencies": ["worker-router"],
  "targets": {
    "build": {
      "executor": "nx:run-commands",
      "options": {
        "command": "npx next-on-pages",
        "cwd": "apps/status"
      },
      "cache": true,
      "inputs": ["default", "^production"],
      "outputs": ["{projectRoot}/.vercel/output"]
    },
    "typecheck": {
      "executor": "nx:run-commands",
      "options": {
        "command": "npx tsc --noEmit -p tsconfig.json",
        "cwd": "apps/status"
      },
      "cache": true
    },
    "lint": {
      "executor": "@nx/eslint:lint",
      "cache": true
    },
    "deploy": {
      "executor": "nx:run-commands",
      "options": {
        "command": "node scripts/deploy.mjs",
        "cwd": "apps/status"
      },
      "dependsOn": [
        "gpu-workers-flux2:deploy-modal",
        "gpu-workers-flux2:deploy-beam",
        "gpu-workers-flux2:deploy-flash",
        "gpu-workers-tiny-sd:deploy-modal",
        "gpu-workers-tiny-sd:deploy-beam",
        "gpu-workers-tiny-sd:deploy-flash",
        "worker-router:deploy"
      ],
      "cache": false
    }
  }
}
```

### 2. `apps/status/scripts/generate-config.mjs` — reads contracts, writes `uptime.config.ts`

This script:
- Reads `dist/apps/gpu-workers-{flux2, tiny_sd}/contract.json` (one of: beam, modal, or flash — takes the first available)
- Hardcodes worker-router domains from `apps/worker-router/scripts/deploy.mjs`
- Generates `apps/status/uptime.config.ts` with monitors array populated
- Falls back gracefully if contract files don't exist yet (empty monitors)

Key URL mappings:
- **GPU workers** (from contract.json): `url` field → monitor target
- **worker-router** (from deploy.mjs): 
  - `https://worker-router-flux2.gyorgy-gutai.workers.dev`
  - `https://worker-router-tinysd.gyorgy-gutai.workers.dev`
- **infra-router** (from wrangler.jsonc): `inference-router` domain

Monitor format:
```typescript
{
  id: '{model}-{provider}',
  name: '{Display Name} ({Provider})',
  method: 'GET',
  target: '<url-from-contract>',
  expectedCodes: [200],
  timeout: 10000,
}
```

### 3. `apps/status/scripts/deploy.mjs` — orchestrates deploy

```
1. node scripts/generate-config.mjs         → generates uptime.config.ts
2. npx next-on-pages                        → builds Pages output
3. npx wrangler pages deploy .vercel/output  → deploys to Pages
```

The deploy command passes:
- `--var DATABASE_ID:<actual-d1-id>` (resolved from Cloudflare account)
- `--var WORKER_ROUTER_FLUX2_URL:<url>`
- `--var WORKER_ROUTER_TINYSD_URL:<url>`
- `--var INFRA_ROUTER_URL:<url>`

### 4. `apps/status/wrangler.toml` — update Pages config

Add Pages-specific deployment config with D1 binding:

```toml
name = "status"
compatibility_date = "2025-04-02"
compatibility_flags = [ "nodejs_compat" ]

vars = {
  DATABASE_ID = "00000000-0000-0000-0000-000000000000",
  WORKER_ROUTER_FLUX2_URL = "https://worker-router-flux2.gyorgy-gutai.workers.dev",
  WORKER_ROUTER_TINYSD_URL = "https://worker-router-tinysd.gyorgy-gutai.workers.dev",
  INFRA_ROUTER_URL = "https://inference-router.gyorgy-gutai.workers.dev"
}

[[d1_databases]]
binding = "STATUS_D1"
database_name = "status_d1"
database_id = "00000000-0000-0000-0000-000000000000"
```

The `DATABASE_ID` var is interpolated at deploy time via `--var DATABASE_ID:<id>`. The Pages deployment config uses this for the runtime D1 binding.

### 5. Remove `apps/status/worker/` directory

Since the Pages deployment bundles the cron worker, the separate worker directory is no longer needed. The worker code (`worker/src/`) will be bundled by `next-on-pages` as part of the Pages deployment via the `__scheduler` route.

**Alternative**: If the separate worker deployment is needed, keep the worker directory but ensure the generate-config script also copies `uptime.config.ts` into the worker output directory.

## Deploy Sequence

```bash
# Deploy everything — status deploys last automatically
npx nx run gpu-workers-flux2:deploy-flash   # writes contract.json
npx nx run gpu-workers-tiny-sd:deploy-modal # writes contract.json
npx nx run worker-router:deploy              # reads contracts, deploys
npx nx run status:deploy                     # reads contracts + known URLs, deploys
```

Or the full chain:
```bash
npx nx run-many --target=deploy --projects=gpu-workers-flux2,gpu-workers-tiny-sd,worker-router,status
```

## Monitor URLs (what gets polled)

| Source | URL Pattern | Monitor ID Format |
|--------|-------------|-------------------|
| GPU workers contract.json | `{contract.url}` | `{model}-{provider}` |
| worker-router | `https://worker-router-{env}.gyorgy-gutai.workers.dev` | `worker-router-{env}` |
| infra-router | `https://inference-router.gyorgy-gutai.workers.dev` | `infra-router` |

The `contract.json` file contains the `url` field from the deploy output script (e.g., `https://endpoints.runpod.io/v2/{endpointId}` for flash, `https://{project}.app.beam.cloud` for beam, `https://{app}--queue-api.modal.run` for modal).

## Implementation Order

1. Create `apps/status/scripts/generate-config.mjs`
2. Create `apps/status/scripts/deploy.mjs`
3. Update `apps/status/wrangler.toml` (add vars, Pages config)
4. Create `apps/status/project.json`
5. Remove `apps/status/worker/` directory (bundle via next-on-pages instead)

## Notes

- `uptime.config.ts` is generated at deploy time, NOT committed — it goes in `.gitignore`
- The cron worker polls monitors every minute, reads config from bundled file
- The Pages app reads status data from D1 at runtime (not from config)
- If no contracts exist yet (local dev), generate-config produces empty monitors array
