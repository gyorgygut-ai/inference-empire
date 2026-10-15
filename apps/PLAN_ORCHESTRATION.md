# 🎯 Model Orchestration — Plan

Idempotent target state. Every bullet is an assertion that holds after apply.

## 🗂️ Env files

- 📁 One file per `{model}/{env}`: `dist/flux2/dev.env`, `dist/flux2/deploy.env`, `dist/krea2/dev.env`, `dist/krea2/deploy.env`
- 🔑 Keys: `MODAL_WORKER_URL`, `BEAM_WORKER_URL`, `ROUTER_AUTH_TOKEN`, `ROUTER_URL`
- 🔑 `FLASH_WORKER_URL` present in env files whose model has a flash worker
- 🔐 Router auth key name is `ROUTER_AUTH_TOKEN`

## 🛠️ tools/update-env-file.ts

- ✍️ CLI: `update-env-file <file> <KEY> <value>` → sets `KEY=value` in `<file>`
- 📁 Creates the parent directory and the file when absent
- ♻️ Replaces the existing line when `<KEY>` is already present
- 🔒 Sequence: `proper-lockfile` lock → read → replace/insert → write tmp file → rename
- 🎯 The only code that writes env files

## ⚙️ tools/orchestrator (nx plugin)

- 🧩 Executor `orchestrator:run-command` (the plugin's only executor)
- 📥 Options: `{ command, args?, envFile, envKey? }`
- 🧵 Spawns `command` with `args` (no shell, no composition)
- 📖 Child env = `{ ...process.env, ...dotenv.parse(envFile) }`
- 🎯 With `envKey`: first stdout line is the value → written via `update-env-file`
- ⏳ Signals ready once the value line is captured; process stays alive for continuous targets
- 📤 Command contract: exactly one value on stdout; all logs on stderr

## 🧭 apps/router (project.json)

- 🎯 Targets (complete set):
  - `dev-{model}`: `orchestrator:run-command`, `continuous: true`, `envFile: dist/{model}/dev.env`, `envKey: ROUTER_URL`, `args: ["--port=5040"]` for flux2 / `["--port=5042"]` for krea2
  - `deploy-{model}`: `orchestrator:run-command`, `envFile: dist/{model}/deploy.env`, `envKey: ROUTER_URL`
  - `generate-{model}-auth-token`: `orchestrator:run-command`, `envFile: dist/{model}/{env}.env`, `envKey: ROUTER_AUTH_TOKEN`
- 🔗 `dev-{model}` `dependsOn` `worker-{model}:deploy-modal`, `worker-{model}:deploy-beam` (flux2), `generate-{model}-auth-token`, with `params: "forward"` so `envFile` is shared
- 🧱 Inputs/outputs set for `cache` and `continuous` on every target

## 🧭 apps/router (source)

- 🖥️ `src/serve.ts`: `@hono/node-server` `serve({ fetch: (req) => router.fetch(req, env), port })`
- 🔌 `port` read from the `--port` arg
- 📢 Prints `http://127.0.0.1:{port}` on stdout after listening (this is the ready signal)
- 📤 Logs go to stderr
- 🧭 `env.schema.ts` validates `{ MODAL_WORKER_URL?, BEAM_WORKER_URL?, FLASH_WORKER_URL?, ROUTER_AUTH_TOKEN }`
- 🎛️ Model binding is build-time: the per-model entry imports its own generated contract

## 📦 packages/contracts (nx project)

- 🗂️ Project with target `contracts:generate-{model}-api-types`
- 🧬 Merges `packages/contracts/api-task-queue.json` + `packages/contracts/{model}/inference.json`
- 📤 Output: `packages/contracts/generated/{model}_api.ts` (gitignored)
- 🧱 `inputs` = the two json files; `outputs` = the generated file
- 📎 Router and face-value depend on the contracts project and import via `@packages/contracts/generated/{model}_api`

## 💬 apps/face-value (project.json)

- 💻 `dev`: `orchestrator:run-command` wrapping `next dev`, `envFile: dist/flux2/dev.env`, `continuous: true`
- 🚀 `deploy`: `orchestrator:run-command` wrapping `deploy-vercel`, `envFile: dist/flux2/deploy.env`
- 🔗 `dev` `dependsOn` `router:dev-flux2` with `params: "forward"` (shares `envFile`)
- 🔑 Consumes `ROUTER_URL`, `ROUTER_AUTH_TOKEN`

## 🚀 Deploy

- 🧭 `router:deploy-{model}` → `deploy-vercel`, writes `ROUTER_URL` (deployed URL) via `envKey`
- 💬 `face-value:deploy` → `deploy-vercel` from repo root
- 📨 `deploy-vercel` forwards `RUNTIME_KEYS` (`ROUTER_AUTH_TOKEN`, `ROUTER_URL`, `MODAL/BEAM/FLASH_WORKER_URL`) from `process.env` as `-e`
- 🔐 Vercel secrets supplied via env: `*_VERCEL_TOKEN`, `*_VERCEL_ORG_ID`, `*_VERCEL_PROJECT_ID`

## 🔗 Wiring

- 🧭 `dependsOn` uses `^generate-{model}-api-types` wildcards; router and face-value declare a dependency on `packages/contracts`
- ⚡ FLASH targets and scripts exist; no router target depends on a flash worker
- 🧰 `deploy-*`, `serve-*`, `generate-*` scripts take explicit args and are reusable across models
- 🧱 Every target sets nx-native `inputs`, `outputs`, `cache`, `continuous`

## 📝 Specs

- 📄 `apps/router/AGENTS.md`: target set above; env keys above
- 📄 `apps/WORKERS.md`: dev/deploy command contract (one value on stdout)
- 📄 `apps/face-value/AGENTS.md`: env keys + generated-types import path
- 📄 `apps/ACCEPTANCE.md`: per-target criteria

## ✅ Verification

- 🧭 Clear `dist` + generated types → run `router:dev-flux2` → assert `apps/ACCEPTANCE.md`
- 🧭 Run `router:dev-flux2` + `router:dev-krea2` in parallel (5040 + 5042) → assert `apps/ACCEPTANCE.md`
- 💬 Clear `dist` + generated types → run `face-value:dev` → assert `apps/ACCEPTANCE.md`
- 💬 Run `face-value:deploy` → assert `apps/ACCEPTANCE.md`
