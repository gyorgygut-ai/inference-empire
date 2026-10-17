# Inference Empire

**Value Proposition**: Monorepo for inference workers + frontends + tooling.

- **ACTIVATE**: `./opencode/skills/nx-workspace`
- **Specs**: always authoritive. Code must match specs
- **Not gaps**: good code without specs, example names not coded

---

## Projects

- [Workers](./apps/WORKERS.md)
- [Router](./apps/router/AGENTS.md)
- [Face Value](./apps/face-value/AGENTS.md)

---

## Root `.env`

- `HF_TOKEN`
- `R2_ACCESS_KEY`
- `R2_SECRET_KEY`
- `R2_ENDPOINT`
- `R2_BUCKET`
- `FLUX2_ROUTER_URL`
- `FLUX2_ROUTER_VERCEL_TOKEN`
- `FLUX2_ROUTER_VERCEL_ORG_ID`
- `FLUX2_ROUTER_VERCEL_PROJECT_ID`
- `KREA_ROUTER_URL`
- `KREA2_ROUTER_VERCEL_TOKEN`
- `KREA2_ROUTER_VERCEL_ORG_ID`
- `KREA2_ROUTER_VERCEL_PROJECT_ID`
- `FACE_VALUE_VERCEL_TOKEN`
- `FACE_VALUE_VERCEL_ORG_ID`
- `FACE_VALUE_VERCEL_PROJECT_ID`

## Acceptance Criteria

**face-value:dev**:

- [ ] `{workspaceRoot}/dist/flux2/dev.env`:
  - [ ] `packages/schemas/flux2/schema.ts` exists
  - [ ] `MODAL_WORKER_URL` is a valid modal worker url
  - [ ] `BEAM_WORKER_URL` is a valid beam worker url
  - [ ] `ROUTER_AUTH_TOKEN` equals `router:generate-auth-token`
- [ ] `router:dev-flux2` listening on `.env.FLUX2_ROUTER_URL`
- [ ] `.env.FLUX2_ROUTER_URL` accepts `ROUTER_AUTH_TOKEN`
- [ ] `face-value:dev` 200 at `http://127.0.0.1:3000`
- [ ] `face-value:dev` requests `router:dev-flux2` url
- [ ] `face-value:dev` uses `ROUTER_AUTH_TOKEN`

**face-value:deploy**:

- [ ] `{workspaceRoot}/dist/flux2/deploy.env`:
  - [ ] `packages/schemas/flux2/schema.ts` exists
  - [ ] `MODAL_WORKER_URL` is a valid modal worker url
  - [ ] `BEAM_WORKER_URL` is a valid beam worker url
  - [ ] `ROUTER_AUTH_TOKEN` equals `router:generate-auth-token`
  - [ ] `ROUTER_URL` accepts `ROUTER_AUTH_TOKEN`
  - [ ] `router:deploy-flux2` listening on `ROUTER_URL`
  - [ ] `ROUTER_URL`+`ROUTER_AUTH_TOKEN` responds
- [ ] `face-value:deploy` 200 at `http://127.0.0.1:3000`
- [ ] `face-value:deploy` requests `router:deploy-flux2` url
- [ ] `face-value:deploy` uses `ROUTER_AUTH_TOKEN`

---

<!-- nx configuration start-->
<!-- Leave the start & end comments to automatically receive updates. -->

## General Guidelines for working with Nx

- For navigating/exploring the workspace, invoke the `nx-workspace` skill first - it has patterns for querying projects, targets, and dependencies
- When running tasks (for example build, lint, test, e2e, etc.), always prefer running the task through `nx` (i.e. `nx run`, `nx run-many`, `nx affected`) instead of using the underlying tooling directly
- Prefix nx commands with the workspace's package manager (e.g., `pnpm nx build`, `npm exec nx test`) - avoids using globally installed CLI
- You have access to the Nx MCP server and its tools, use them to help the user
- For Nx plugin best practices, check `node_modules/@nx/<plugin>/PLUGIN.md`. Not all plugins have this file - proceed without it if unavailable.
- NEVER guess CLI flags - always check nx_docs or `--help` first when unsure

## Scaffolding & Generators

- For scaffolding tasks (creating apps, libs, project structure, setup), ALWAYS invoke the `nx-generate` skill FIRST before exploring or calling MCP tools

## When to use nx_docs

- USE for: advanced config options, unfamiliar flags, migration guides, plugin configuration, edge cases
- DON'T USE for: basic generator syntax (`nx g @nx/react:app`), standard commands, things you already know
- The `nx-generate` skill handles generator discovery internally - don't call nx_docs just to look up generator syntax

<!-- nx configuration end-->
