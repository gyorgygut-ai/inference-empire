# Inference Empire

This is a monorepo for all my custom inference related code.

## Key Components / Subfolders

- [Chat GUI](./apps/chat-ui/AGENTS.md)
- [Cloud GPU Workers](./apps/gpu-workers/AGENTS.md)
- [Inference Router Proxy](./apps/infra-router/AGENTS.md) (legacy copy: `./archive/proxy/AGENTS.md`)

---

## Core Nx Commands

- `npm run test-unit` — run all unit tests (Nx orchestrated).
- `npm run test-e2e` — run live e2e tests (costs GPU/provider calls).
- `npm run lint` — lint everything.
- `npm run build` — build everything.
- `npm run generate` — run the worker prompt generator (`nx run cli:generate`, code in `tools/cli/generate.py`).
- `npx nx run <project>:<target>` — run one target, e.g. `npx nx run chat-ui:build`.
- `npx nx show projects` — list all projects (source of truth, never hardcode).
- `npx nx show project <name>` — targets, executors and tags for one project.
- `npx nx graph` — visual project/task dependency graph.
- `npx nx g workspace-plugin:<gpu-family|ts-app|ts-lib|migrate-dir> [--dry-run]` — new or migrated projects; never hand-write `project.json`.
- `npx nx run types:generate` — regenerate TS types after any contract edit; commit `packages/types/src/generated.ts`.

Python selection is filename-based (`-k "not e2e"` / `-k "e2e"`); never invent
`--target` flags and never edit tests to fit the runner. `archive/` is frozen
legacy — never edit.

---

## Golden Rules

- Use conventional commits
- Specs are authoritative: code must match them
- Exact touched files and lines to finish task; no less, no more
- Adherence to specs, key decisions and golden rules is non-negotiable


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
