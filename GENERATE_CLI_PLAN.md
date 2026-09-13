# Plan: TypeScript Rewrite of `tools/cli/generate.py` (In-Place)

## Architecture
```
tools/cli/                           # Same project name "cli", binary "generate"
├── project.json                     # Update: @nx/js:node executor
├── package.json                     # bin: generate, deps: commander, js-yaml, glob, @inference/contracts, @inference/types
├── tsconfig.json                    # extends ../../tsconfig.base.json
└── src/
    ├── main.ts                      # CLI entry (replaces generate.py main)
    ├── frontmatter.ts               # parse YAML frontmatter (js-yaml)
    ├── contracts.ts                 # find_contract (reads @inference/contracts JSON)
    ├── workers.ts                   # find_workers (glob), select_worker (env var, no fzf)
    ├── invoke.ts                    # HTTP POST to worker endpoint
    ├── media.ts                     # resolve_media_value (paths → base64)
    └── config.ts                    # monorepo root from env/config
```

## Invocation Strategy: HTTP via infra-router (TypeScript)
- **CLI calls `POST http://localhost:8787/infer`** (local infra-router via `wrangler dev`)
- infra-router routes to Beam/Modal/Flash using existing logic (`apps/infra-router/`)
- No Python subprocess, no worker refactoring needed
- User runs `wrangler dev` in infra-router separately

## Worker Selection (No fzf)
- `WORKER_PROVIDER=beam|modal|flash` env var forces provider
- Default: first matching worker for contract

## Global Install
```bash
nx run cli:build          # → tools/cli/dist/main.js
npm pack tools/cli        # → inference-cli-*.tgz
npm install -g ./inference-cli-*.tgz
```

## Config (Global Use)
```json
// ~/.config/generate/config.json
{
  "monorepoRoot": "/path/to/inference-tooling",
  "routerUrl": "http://localhost:8787"
}
```
Env overrides: `INFERENCE_TOOLING_ROOT`, `GENERATE_ROUTER_URL`

## Nx Targets (Updated project.json)
```json
{
  "targets": {
    "build": { "executor": "@nx/js:tsc", "options": { "rootDir": "src", "outDir": "dist" } },
    "generate": { "executor": "nx:run-commands", "options": { "command": "node dist/main.js" } },
    "lint": { "executor": "nx:run-commands", "options": { "command": "eslint src/**/*.ts" } }
  }
}
```

## Dependencies
```json
{
  "dependencies": {
    "commander": "^12.x",
    "js-yaml": "^4.x",
    "glob": "^11.x",
    "@inference/contracts": "*",
    "@inference/types": "*"
  },
  "devDependencies": {
    "@types/js-yaml": "^4.x",
    "@types/node": "^22.x",
    "typescript": "^5.x"
  }
}
```